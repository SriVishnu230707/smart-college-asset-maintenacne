"""Disposable Core declarations for Step 16, separate from future migrations."""

from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Index, MetaData,
    String, Table, Text, Uuid, text,
)

SCHEMA = "college_step16"
NAMING = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}
metadata = MetaData(schema=SCHEMA, naming_convention=NAMING)

departments = Table(
    "departments", metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("code", String(20), nullable=False, unique=True),
    Column("name", String(150), nullable=False),
    Column("is_archived", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name="code_canonical"),
    CheckConstraint("name !~ '^[[:space:]]*$'", name="name_nonblank"),
)
asset_categories = Table(
    "asset_categories", metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("code", String(30), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("is_archived", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name="code_canonical"),
    CheckConstraint("name !~ '^[[:space:]]*$'", name="name_nonblank"),
)
assets = Table(
    "assets", metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("asset_code", String(50), nullable=False, unique=True),
    Column("name", String(150), nullable=False),
    Column("department_id", Uuid, ForeignKey(f"{SCHEMA}.departments.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False),
    Column("category_id", Uuid, ForeignKey(f"{SCHEMA}.asset_categories.id", ondelete="RESTRICT", onupdate="RESTRICT"), nullable=False),
    Column("location", String(200)),
    Column("status", Text, nullable=False, default="active", server_default=text("'active'")),
    CheckConstraint("asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'", name="asset_code_canonical"),
    CheckConstraint("name !~ '^[[:space:]]*$'", name="name_nonblank"),
    CheckConstraint("status = 'active' OR status = 'under_maintenance' OR status = 'retired'", name="status_allowed"),
    info={"purpose": "disposable Step 16 metadata exercise"},
)
Index(None, assets.c.department_id)
Index(None, assets.c.category_id)
