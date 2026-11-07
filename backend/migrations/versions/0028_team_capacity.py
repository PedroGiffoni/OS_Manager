"""Allow capacity planning against an internal user group with a roster snapshot."""

from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


RESOURCE_CHECK = (
    "(supplier_id IS NOT NULL AND user_id IS NULL AND group_id IS NULL) OR "
    "(supplier_id IS NULL AND user_id IS NOT NULL AND group_id IS NULL) OR "
    "(supplier_id IS NULL AND user_id IS NULL AND group_id IS NOT NULL)"
)


def upgrade():
    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.drop_constraint("ck_capacity_one_resource", type_="check")

    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("group_member_ids", sa.JSON(), server_default="[]", nullable=False)
        )
        batch_op.create_foreign_key(
            "fk_resource_capacity_group_id_user_groups",
            "user_groups",
            ["group_id"],
            ["id"],
        )
        batch_op.create_check_constraint("ck_capacity_one_resource", RESOURCE_CHECK)
        batch_op.create_index("ix_resource_capacity_group_id", ["group_id"])


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT COUNT(*) FROM resource_capacity WHERE group_id IS NOT NULL")):
        raise RuntimeError(
            "Não é possível remover capacidade de equipe enquanto houver períodos registrados. "
            "Exporte ou exclua esses registros com aprovação antes do downgrade."
        )
    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.drop_index("ix_resource_capacity_group_id")
        batch_op.drop_constraint("ck_capacity_one_resource", type_="check")
        batch_op.drop_constraint(
            "fk_resource_capacity_group_id_user_groups", type_="foreignkey"
        )
        batch_op.drop_column("group_member_ids")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("resource_capacity") as batch_op:
        batch_op.create_check_constraint(
            "ck_capacity_one_resource",
            "(supplier_id IS NULL) != (user_id IS NULL)",
        )
