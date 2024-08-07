"""

Revision ID: bf26afac872d
Revises: 1ebfe5e4cf1c
Create Date: 2024-07-03 15:27:42.903931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bf26afac872d"
down_revision: Union[str, None] = "1ebfe5e4cf1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("projects", sa.Column("overlap_percent", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("gsd_cm_px", sa.Float(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("gimble_angles_degrees", sa.ARRAY(sa.SmallInteger()), nullable=True),
    )
    op.drop_column("projects", "overlap")
    op.drop_column("projects", "gimble_angles")
    op.drop_column("projects", "gsd")
    op.drop_index("ix_tasks_locked_by", table_name="tasks")
    op.drop_index("ix_tasks_mapped_by", table_name="tasks")
    op.drop_index("ix_tasks_validated_by", table_name="tasks")
    op.drop_constraint("fk_users_validator", "tasks", type_="foreignkey")
    op.drop_constraint("fk_users_mapper", "tasks", type_="foreignkey")
    op.drop_constraint("fk_users_locked", "tasks", type_="foreignkey")
    op.drop_column("tasks", "locked_by")
    op.drop_column("tasks", "validated_by")
    op.drop_column("tasks", "mapped_by")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "tasks",
        sa.Column("mapped_by", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("validated_by", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("locked_by", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key("fk_users_locked", "tasks", "users", ["locked_by"], ["id"])
    op.create_foreign_key("fk_users_mapper", "tasks", "users", ["mapped_by"], ["id"])
    op.create_foreign_key(
        "fk_users_validator", "tasks", "users", ["validated_by"], ["id"]
    )
    op.create_index("ix_tasks_validated_by", "tasks", ["validated_by"], unique=False)
    op.create_index("ix_tasks_mapped_by", "tasks", ["mapped_by"], unique=False)
    op.create_index("ix_tasks_locked_by", "tasks", ["locked_by"], unique=False)
    op.add_column(
        "projects",
        sa.Column(
            "gsd", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "gimble_angles",
            postgresql.ARRAY(sa.SMALLINT()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "overlap",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_column("projects", "gimble_angles_degrees")
    op.drop_column("projects", "gsd_cm_px")
    op.drop_column("projects", "overlap_percent")
    # ### end Alembic commands ###
