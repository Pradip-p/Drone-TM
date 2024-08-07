import json
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.projects import project_schemas
from app.db import db_models
from loguru import logger as log
import shapely.wkb as wkblib
from shapely.geometry import shape
from fastapi import HTTPException
from app.utils import merge_multipolygon, str_to_geojson
from fmtm_splitter.splitter import split_by_square
from fastapi.concurrency import run_in_threadpool
from app.db import database
from fastapi import Depends
from asyncio import gather
from databases import Database


async def create_project_with_project_info(
    db: Database, project_metadata: project_schemas.ProjectIn
):
    """Create a project in database."""
    project_id = uuid.uuid4()
    query = """
        INSERT INTO projects (
            id, author_id, name, short_description, description, per_task_instructions, status, visibility, outline, dem_url, created
        )
        VALUES (
            :project_id,
            :author_id,
            :name,
            :short_description,
            :description,
            :per_task_instructions,
            :status,
            :visibility,
            :outline,
            :dem_url,
            CURRENT_TIMESTAMP
        )
        RETURNING id
    """
    # new_project_id = await db.execute(query)
    new_project_id = await db.execute(
        query,
        values={
            "project_id": project_id,
            "author_id": str(110878106282210575794),  # TODO: update this
            "name": project_metadata.name,
            "short_description": project_metadata.short_description,
            "description": project_metadata.description,
            "per_task_instructions": project_metadata.per_task_instructions,
            "status": "DRAFT",
            "visibility": "PUBLIC",
            "outline": str(project_metadata.outline),
            "dem_url": project_metadata.dem_url,
        },
    )

    if not new_project_id:
        raise HTTPException(status_code=500, detail="Project could not be created")
    # Fetch the newly created project using the returned ID
    select_query = f"""
        SELECT id, name, short_description, description, per_task_instructions, outline
        FROM projects
        WHERE id = '{new_project_id}'
    """
    new_project = await db.fetch_one(query=select_query)
    return new_project


async def get_project_by_id(
    db: Session = Depends(database.get_db), project_id: Optional[int] = None
) -> db_models.DbProject:
    """Get a single project by id."""
    db_project = (
        db.query(db_models.DbProject)
        .filter(db_models.DbProject.id == project_id)
        .first()
    )
    return await convert_to_app_project(db_project)


async def get_projects(
    db: Database,
    skip: int = 0,
    limit: int = 100,
):
    """Get all projects."""
    raw_sql = """
        SELECT id, name, short_description, description, per_task_instructions, outline
        FROM projects
        ORDER BY id DESC
        OFFSET :skip
        LIMIT :limit;
        """
    db_projects = await db.fetch_all(raw_sql, {"skip": skip, "limit": limit})
    return await convert_to_app_projects(db_projects)


# async def get_projects(
#     db: Session,
#     skip: int = 0,
#     limit: int = 100,
# ):
#     """Get all projects."""
#     db_projects = (
#         db.query(db_models.DbProject)
#         .order_by(db_models.DbProject.id.desc())
#         .offset(skip)
#         .limit(limit)
#         .all()
#     )
#     project_count = db.query(db_models.DbProject).count()
#     return project_count, await convert_to_app_projects(db_projects)


async def convert_to_app_projects(
    db_projects: List[db_models.DbProject],
) -> List[project_schemas.ProjectOut]:
    """Legacy function to convert db models --> Pydantic.

    TODO refactor to use Pydantic model methods instead.
    """
    if db_projects and len(db_projects) > 0:

        async def convert_project(project):
            return await convert_to_app_project(project)

        app_projects = await gather(
            *[convert_project(project) for project in db_projects]
        )
        return [project for project in app_projects if project is not None]
    else:
        return []


async def convert_to_app_project(db_project: db_models.DbProject):
    """Legacy function to convert db models --> Pydantic."""
    if not db_project:
        log.debug("convert_to_app_project called, but no project provided")
        return None
    app_project = db_project

    if db_project.outline:
        app_project.outline_geojson = str_to_geojson(
            db_project.outline, {"id": db_project.id}, db_project.id
        )
    return app_project


async def create_tasks_from_geojson(
    db: Database,
    project_id: uuid.UUID,
    boundaries: str,
):
    """Create tasks for a project, from provided task boundaries."""
    try:
        if isinstance(boundaries, str):
            boundaries = json.loads(boundaries)

        # Update the boundary polyon on the database.
        if boundaries["type"] == "Feature":
            polygons = [boundaries]
        else:
            polygons = boundaries["features"]
        log.debug(f"Processing {len(polygons)} task geometries")
        for index, polygon in enumerate(polygons):
            try:
                # If the polygon is a MultiPolygon, convert it to a Polygon
                if polygon["geometry"]["type"] == "MultiPolygon":
                    log.debug("Converting MultiPolygon to Polygon")
                    polygon["geometry"]["type"] = "Polygon"
                    polygon["geometry"]["coordinates"] = polygon["geometry"][
                        "coordinates"
                    ][0]

                task_id = str(uuid.uuid4())
                query = """
                    INSERT INTO tasks (id, project_id, outline, project_task_index)
                    VALUES (:id, :project_id, :outline, :project_task_index);"""

                result = await db.execute(
                    query,
                    values={
                        "id": task_id,
                        "project_id": project_id,
                        "outline": wkblib.dumps(shape(polygon["geometry"]), hex=True),
                        "project_task_index": index + 1,
                    },
                )

                if result:
                    log.debug(
                        "Created database task | "
                        f"Project ID {project_id} | "
                        f"Task index {index}"
                    )
                    log.debug(
                        "COMPLETE: creating project boundary, based on task boundaries"
                    )
                    return True
            except Exception as e:
                log.exception(e)
                raise HTTPException(e) from e
    except Exception as e:
        log.exception(e)
        raise HTTPException(e) from e


async def preview_split_by_square(boundary: str, meters: int):
    """Preview split by square for a project boundary.

    Use a lambda function to remove the "z" dimension from each
    coordinate in the feature's geometry.
    """
    boundary = merge_multipolygon(boundary)

    return await run_in_threadpool(
        lambda: split_by_square(
            boundary,
            meters=meters,
        )
    )
