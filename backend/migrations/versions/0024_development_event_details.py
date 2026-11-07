"""Store provider-neutral development metadata, not raw webhook payloads."""

from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "development_events",
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade():
    with op.batch_alter_table("development_events") as batch_op:
        batch_op.drop_column("metadata")
