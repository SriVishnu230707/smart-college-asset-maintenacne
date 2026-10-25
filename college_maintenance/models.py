"""Typed column mappings; schema installation belongs to reviewed migrations."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, MetaData, Numeric, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
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
    assets: Mapped[list["Asset"]] = relationship(back_populates="department", passive_deletes="all")


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
    reported_tickets: Mapped[list["MaintenanceTicket"]] = relationship(back_populates="reporter", foreign_keys="MaintenanceTicket.reported_by_id", passive_deletes="all")
    assigned_tickets: Mapped[list["MaintenanceTicket"]] = relationship(back_populates="assignee", foreign_keys="MaintenanceTicket.assigned_to_id", passive_deletes="all")


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'", name="asset_code"),
        CheckConstraint("name !~ '^[[:space:]]*$'", name="name"),
        CheckConstraint("status IN ('active', 'under_maintenance', 'retired')", name="status"),
        CheckConstraint("condition_note !~ '^[[:space:]]*$'", name="condition_note"),
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
    condition_note: Mapped[str] = mapped_column(Text, server_default=text("'Not assessed'"))


class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"
    __table_args__ = (
        Index("ix_maintenance_tickets_created_at_id", "created_at", "id"),
        CheckConstraint("title !~ '^[[:space:]]*$'", name="title"),
        CheckConstraint("description !~ '^[[:space:]]*$'", name="description"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name="priority"),
        CheckConstraint("status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')", name="status"),
        CheckConstraint("version > 0", name="version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    version: Mapped[int] = mapped_column(server_default=text('1'))
    __mapper_args__ = {'version_id_col': version}
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
    verification_note: Mapped[str | None] = mapped_column(Text)
    rework_reason: Mapped[str | None] = mapped_column(Text)

    reporter: Mapped[User] = relationship(back_populates="reported_tickets", foreign_keys=[reported_by_id])
    assignee: Mapped[User | None] = relationship(back_populates="assigned_tickets", foreign_keys=[assigned_to_id])
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="ticket", passive_deletes="all")
    comments: Mapped[list["TicketComment"]] = relationship(back_populates="ticket", passive_deletes="all", order_by="(TicketComment.created_at, TicketComment.id)")


class SparePart(Base):
    __tablename__ = "spare_parts"
    __table_args__ = (
        CheckConstraint("sku = upper(btrim(sku)) AND sku <> ''", name="sku"),
        CheckConstraint("display_name !~ '^[[:space:]]*$'", name="name"),
        CheckConstraint("stock_quantity >= 0 AND reorder_level >= 0", name="stock"),
        CheckConstraint("current_unit_cost >= 0", name="cost"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column("display_name", String(150))
    stock_quantity: Mapped[int] = mapped_column(server_default=text("0"))
    reorder_level: Mapped[int] = mapped_column(server_default=text("0"))
    current_unit_cost: Mapped[Decimal] = mapped_column(Numeric(12,2))
    is_archived: Mapped[bool] = mapped_column(server_default=text("false"))
    usages: Mapped[list["WorkOrderPart"]] = relationship(back_populates="part", passive_deletes="all")


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("status IN ('draft','in_progress','completed')", name="status"),
        CheckConstraint("labor_cost >= 0", name="labor_cost"),
        Index("uq_work_orders_active_ticket", "ticket_id", unique=True, postgresql_where=text("status IN ('draft','in_progress')")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_tickets.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'draft'"))
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), server_default=text("0"))
    completion_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ticket: Mapped[MaintenanceTicket] = relationship(back_populates="work_orders")
    technician: Mapped[User] = relationship()
    part_usages: Mapped[list["WorkOrderPart"]] = relationship(back_populates="work_order", passive_deletes="all")


class WorkOrderPart(Base):
    __tablename__ = "work_order_parts"
    __table_args__ = (
        CheckConstraint("quantity_used > 0", name="quantity"),
        CheckConstraint("unit_cost_at_use >= 0", name="unit_cost"),
    )
    work_order_id: Mapped[UUID] = mapped_column(ForeignKey("work_orders.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True)
    spare_part_id: Mapped[UUID] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT", onupdate="RESTRICT"), primary_key=True, index=True)
    quantity_used: Mapped[int] = mapped_column()
    unit_cost_at_use: Mapped[Decimal] = mapped_column(Numeric(12,2))
    work_order: Mapped[WorkOrder] = relationship(back_populates="part_usages")
    part: Mapped[SparePart] = relationship(back_populates="usages")

    @property
    def line_total(self) -> Decimal:
        return self.quantity_used * self.unit_cost_at_use


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (CheckConstraint("action !~ '^[[:space:]]*$'", name="action"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    ticket_id: Mapped[UUID | None] = mapped_column(ForeignKey("maintenance_tickets.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(Text)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    request_id: Mapped[UUID] = mapped_column(Uuid, server_default=text("gen_random_uuid()"))
    target_type: Mapped[str] = mapped_column(Text, server_default=text("'legacy'"))
    target_id: Mapped[UUID | None] = mapped_column(Uuid)
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    __table_args__ = (CheckConstraint("body !~ '^[[:space:]]*$'", name="body"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_tickets.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    ticket: Mapped[MaintenanceTicket] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()


class AttachmentFields:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))
    storage_key: Mapped[str] = mapped_column(String(32), unique=True)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column()
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT", onupdate="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class TicketAttachment(AttachmentFields, Base):
    __tablename__ = 'ticket_attachments'
    __table_args__ = (CheckConstraint('size > 0 AND size <= 1048576', name='size'),)
    ticket_id: Mapped[UUID] = mapped_column(ForeignKey('maintenance_tickets.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)


class WorkOrderAttachment(AttachmentFields, Base):
    __tablename__ = 'work_order_attachments'
    __table_args__ = (CheckConstraint('size > 0 AND size <= 1048576', name='size'),)
    work_order_id: Mapped[UUID] = mapped_column(ForeignKey('work_orders.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)


class Supplier(Base):
    __tablename__ = 'suppliers'
    __table_args__ = (CheckConstraint("name !~ '^[[:space:]]*$' AND contact !~ '^[[:space:]]*$'", name='details'),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(server_default=text('false'))


class InventoryMovement(Base):
    __tablename__ = 'inventory_movements'
    __table_args__ = (
        CheckConstraint("(kind='opening' AND quantity_delta>0 AND supplier_id IS NULL AND work_order_id IS NULL) OR (kind='receipt' AND quantity_delta>0 AND supplier_id IS NOT NULL AND work_order_id IS NULL) OR (kind='consume' AND quantity_delta<0 AND work_order_id IS NOT NULL AND supplier_id IS NULL) OR (kind='adjustment' AND quantity_delta<>0 AND reason !~ '^[[:space:]]*$' AND reason IS NOT NULL AND supplier_id IS NULL AND work_order_id IS NULL)", name='context'),
        CheckConstraint("actor_id IS NOT NULL OR (is_legacy AND kind='opening')", name='actor'),
        Index('uq_inventory_movements_opening','spare_part_id',unique=True,postgresql_where=text("kind='opening'")),
        Index('uq_inventory_movements_consume','work_order_id','spare_part_id',unique=True,postgresql_where=text("kind='consume'")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    spare_part_id: Mapped[UUID] = mapped_column(ForeignKey('spare_parts.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey('suppliers.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)
    work_order_id: Mapped[UUID | None] = mapped_column(ForeignKey('work_orders.id', ondelete='RESTRICT', onupdate='RESTRICT'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    quantity_delta: Mapped[int] = mapped_column()
    reason: Mapped[str | None] = mapped_column(Text)
    is_legacy: Mapped[bool] = mapped_column(server_default=text('false'))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
