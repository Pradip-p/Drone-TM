from pydantic import BaseModel
from app.models.enums import EventType, HTTPStatus, State
import uuid
from datetime import datetime
from psycopg import Connection
from loguru import logger as log
from fastapi import HTTPException
from psycopg.rows import class_row, dict_row
from typing import Optional


class NewEvent(BaseModel):
    event: EventType
    comment: Optional[str] = None


class TaskState(BaseModel):
    task_id: uuid.UUID
    state: str
    project_id: uuid.UUID

    @staticmethod
    async def get_all_tasks(db: Connection, project_id: uuid.UUID):
        async with db.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """SELECT id FROM tasks WHERE project_id = %(project_id)s""",
                {"project_id": str(project_id)},
            )

            data = await cur.fetchall()

            # Extracting the list of IDs from the data
            task_ids = [task["id"] for task in data]

            return task_ids

    @staticmethod
    async def all(db: Connection, project_id: uuid.UUID):
        async with db.cursor(row_factory=class_row(TaskState)) as cur:
            await cur.execute(
                """SELECT DISTINCT ON (task_id) project_id, task_id, state
                FROM task_events
                WHERE project_id = %(project_id)s
                ORDER BY task_id, created_at DESC
            """,
                {"project_id": project_id},
            )

            existing_tasks = await cur.fetchall()
            # Get all task_ids from the tasks table
            task_ids = await TaskState.get_all_tasks(db, project_id)
            # Create a set of existing task_ids for quick lookup
            existing_task_ids = {task.task_id for task in existing_tasks}

            # task ids that are not in task_events table
            remaining_task_ids = [x for x in task_ids if x not in existing_task_ids]

            # Add missing tasks with state as "UNLOCKED_FOR_MAPPING"
            remaining_tasks = [
                {
                    "project_id": str(project_id),
                    "task_id": task_id,
                    "state": State.UNLOCKED_TO_MAP.name,
                }
                for task_id in remaining_task_ids
            ]

            # Combine both existing tasks and remaining tasks
            combined_tasks = existing_tasks + remaining_tasks
            return combined_tasks


class UserTasksStatsOut(BaseModel):
    task_id: uuid.UUID
    task_area: float
    created_at: datetime
    state: str
    project_id: uuid.UUID

    @staticmethod
    async def get_tasks_by_user(
        db: Connection, user_id: str, role: str, skip: int = 0, limit: int = 50
    ):
        async with db.cursor(row_factory=class_row(UserTasksStatsOut)) as cur:
            await cur.execute(
                """SELECT DISTINCT ON (tasks.id)
                    tasks.id AS task_id,
                    task_events.project_id AS project_id,
                    ST_Area(ST_Transform(tasks.outline, 3857)) / 1000000 AS task_area,
                    task_events.created_at,
                    CASE
                        WHEN task_events.state = 'REQUEST_FOR_MAPPING' THEN 'request logs'
                        WHEN task_events.state = 'LOCKED_FOR_MAPPING' THEN 'ongoing'
                        WHEN task_events.state = 'UNLOCKED_DONE' THEN 'completed'
                        WHEN task_events.state = 'UNFLYABLE_TASK' THEN 'unflyable task'
                        ELSE 'UNLOCKED_TO_MAP'
                    END AS state
                FROM
                    task_events
                LEFT JOIN
                    tasks ON task_events.task_id = tasks.id
                WHERE
                    (
                        %(role)s = 'DRONE_PILOT' AND task_events.user_id = %(user_id)s
                    )
                    OR
                    (
                        %(role)s!= 'DRONE_PILOT' AND task_events.project_id IN (SELECT id FROM projects WHERE author_id = %(user_id)s)
                    )
                ORDER BY
                    tasks.id, task_events.created_at DESC
                OFFSET %(skip)s
                LIMIT %(limit)s;""",
                {"user_id": user_id, "role": role, "skip": skip, "limit": limit},
            )
            try:
                return await cur.fetchall()

            except Exception as e:
                log.exception(e)
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Retrieval failed",
                ) from e
