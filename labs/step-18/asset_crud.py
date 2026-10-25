"""ORM practice on disposable assets; authorization/retirement workflows come later."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from labs.shared.column_models import Asset


def create_asset(session: Session, *, asset_code: str, name: str, department_id: UUID,
                 category_id: UUID, location: str | None = None) -> Asset:
    asset = Asset(asset_code=asset_code, name=name, department_id=department_id,
                  category_id=category_id, location=location)
    session.add(asset)
    session.flush()  # Obtain the generated ID/defaults; caller still owns commit.
    return asset


def get_asset(session: Session, asset_id: UUID) -> Asset | None:
    return session.get(Asset, asset_id)


def list_assets(session: Session, department_id: UUID | None = None) -> list[Asset]:
    statement = select(Asset).order_by(Asset.asset_code)
    if department_id is not None:
        statement = statement.where(Asset.department_id == department_id)
    return list(session.scalars(statement))


def update_asset_location(session: Session, asset_id: UUID, location: str | None) -> Asset | None:
    asset = get_asset(session, asset_id)
    if asset is not None:
        asset.location = location
        session.flush()
    return asset


def delete_fixture_asset(session: Session, asset_id: UUID) -> bool:
    """Practice Session.delete on a disposable fixture, not a retirement use case."""
    asset = get_asset(session, asset_id)
    if asset is None:
        return False
    session.delete(asset)
    session.flush()
    return True
