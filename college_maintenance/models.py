"""Typed column mappings; schema installation belongs to reviewed migrations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, MetaData, String, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name="code"),
        CheckConstraint("name !~ '^[[:space:]]*$'", name="name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_archived: Mapped[bool] = mapped_column(server_default=text("false"))
    assets: Mapped[list["Asset"]] = relationship(back_populates="department")


class AssetCategory(Base):
    __tablename__ = "asset_categories"
    __table_args__ = (
        CheckConstraint("code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'", name="code"),
        CheckConstraint("name !~ '^[[:space:]]*$'", name="name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_archived: Mapped[bool] = mapped_column(server_default=text("false"))


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email)) AND email <> '' AND email !~ '[[:space:]]'", name="email"),
        CheckConstraint("display_name !~ '^[[:space:]]*$'", name="display_name"),
        CheckConstraint("password_hash !~ '^[[:space:]]*$'", name="password_hash"),
        CheckConstraint("role IN ('student', 'technician', 'department_admin', 'super_admin')", name="role"),
        CheckConstraint("role = 'super_admin' OR department_id IS NOT NULL", name="department"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", name="fk_users_department", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'", name="asset_code"),
        CheckConstraint("name !~ '^[[:space:]]*$'", name="name"),
        CheckConstraint("status IN ('active', 'under_maintenance', 'retired')", name="status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    asset_code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", name="fk_assets_department", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    department: Mapped[Department] = relationship(back_populates="assets")
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("asset_categories.id", name="fk_assets_category", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    location: Mapped[str | None] = mapped_column(String(200))


class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"
    __table_args__ = (
        CheckConstraint("title !~ '^[[:space:]]*$'", name="title"),
        CheckConstraint("description !~ '^[[:space:]]*$'", name="description"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name="priority"),
        CheckConstraint("status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')", name="status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", name="fk_tickets_asset", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    reported_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", name="fk_tickets_reporter", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_tickets_assignee", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    # Historical department-at-report, independent of the asset's current owner.
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", name="fk_tickets_department", ondelete="RESTRICT", onupdate="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'open'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
