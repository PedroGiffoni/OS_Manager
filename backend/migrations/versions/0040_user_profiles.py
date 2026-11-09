"""Add self-service profile contacts and avatar."""

from alembic import op
import sqlalchemy as sa


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("contact_email", sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column("contact_phone", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("profile_photo", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("profile_photo_type", sa.String(length=40), nullable=True))
        batch_op.add_column(
            sa.Column("profile_photo_version", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("profile_photo_version")
        batch_op.drop_column("profile_photo_type")
        batch_op.drop_column("profile_photo")
        batch_op.drop_column("contact_phone")
        batch_op.drop_column("contact_email")
        batch_op.drop_column("display_name")
