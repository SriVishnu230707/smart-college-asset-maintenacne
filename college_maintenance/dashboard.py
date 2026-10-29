"""Same-origin dashboard and bounded projections using the API's read scopes."""
from pathlib import Path
from uuid import UUID

from fastapi import Depends, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from college_maintenance.models import Asset, Department, MaintenanceTicket, User
from college_maintenance.reads import scope_for_actor, ticket_query

STATIC = Path(__file__).with_name('static')


def install_dashboard(app, actor_id, session_dependency):
    app.mount('/static', StaticFiles(directory=STATIC), name='dashboard-static')

    @app.get('/', include_in_schema=False)
    def dashboard_page():
        return FileResponse(STATIC / 'index.html', headers={
            'Cache-Control': 'no-store',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            'X-Content-Type-Options': 'nosniff',
        })

    @app.get('/me')
    def current_user(identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            scope = scope_for_actor(session, identity)
            user = session.get(User, scope.user_id)
            department = session.get(Department, scope.department_id) if scope.department_id else None
            return dict(id=user.id, name=user.display_name, role=scope.role,
                        department=department.name if department else 'All departments')

    @app.get('/dashboard/summary')
    def summary(identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            visible = ticket_query(scope_for_actor(session, identity)).subquery('visible_tickets')
            active = visible.c.status.not_in(('closed', 'rejected'))
            row = session.execute(select(
                func.count().label('total'),
                func.count().filter(active).label('active'),
                func.count().filter(active, visible.c.priority.in_(('high', 'critical'))).label('urgent'),
                func.count().filter(visible.c.status == 'awaiting_verification').label('awaiting_verification'),
                func.count().filter(visible.c.status == 'closed').label('closed'),
            ).select_from(visible)).mappings().one()
            return dict(row)

    @app.get('/assets')
    def assets(q: str = Query('', max_length=150), limit: int = Query(50, ge=1, le=100),
               offset: int = Query(0, ge=0, le=100000),
               identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            scope = scope_for_actor(session, identity)
            query = select(Asset.id, Asset.name, Asset.asset_code, Asset.status, Asset.location,
                           Department.name.label('department')).join(Department, Asset.department_id == Department.id)
            if scope.role != 'super_admin':
                query = query.where(Asset.department_id == scope.department_id)
            if q.strip():
                query = query.where(Asset.name.icontains(q.strip(), autoescape=True) | Asset.asset_code.icontains(q.strip(), autoescape=True))
            rows = session.execute(query.order_by(Asset.asset_code, Asset.id).offset(offset).limit(limit+1)).mappings().all()
            return dict(items=[dict(row) for row in rows[:limit]],
                        next_offset=offset+limit if len(rows) > limit else None)

    @app.get('/dashboard/technicians')
    def technicians(department_id: UUID | None = None, identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            scope = scope_for_actor(session, identity)
            if scope.role not in {'department_admin', 'super_admin'}:
                raise PermissionError('Technician selection requires administrator access')
            query = select(User.id, User.display_name.label('name')).where(User.role == 'technician', User.is_active)
            if scope.role != 'super_admin':
                query = query.where(User.department_id == scope.department_id)
            if department_id is not None:
                query = query.where(User.department_id == department_id)
            return [dict(row) for row in session.execute(query.order_by(User.display_name, User.id).limit(100)).mappings()]
