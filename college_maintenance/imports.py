"""Explicit asset-import policy; the caller owns the outer transaction."""
from uuid import UUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from college_maintenance.models import Asset

def asset_values(row):
    if set(row)-{'asset_code','name','department_id','category_id','status'}:raise ValueError('Unknown import field')
    code=str(row['asset_code']).strip().upper();name=str(row['name']).strip()
    if not code or not name or len(code)>50 or len(name)>150:raise ValueError('Invalid asset identity')
    status=row.get('status','active')
    if status not in {'active','under_maintenance','retired'}:raise ValueError('Invalid asset status')
    return dict(asset_code=code,name=name,department_id=UUID(str(row['department_id'])),category_id=UUID(str(row['category_id'])),status=status)

def import_assets(session,scope,rows,*,policy='atomic'):
    if scope.role!='super_admin':raise PermissionError('Import requires Super Admin')
    if policy not in {'atomic','reject_rows'}:raise ValueError('Unknown import policy')
    result={'inserted':0,'duplicates':0,'rejected':[]}
    for number,row in enumerate(rows,1):
        def execute():
            values=asset_values(row)
            return session.scalar(insert(Asset).values(**values).on_conflict_do_nothing(index_elements=[Asset.asset_code]).returning(Asset.id))
        try:
            if policy=='reject_rows':
                # begin_nested flushes preexisting pending state; caller must
                # establish a clean unit of work before a row-rejection import.
                with session.begin_nested():identity=execute()
            else:identity=execute()
            result['inserted' if identity else 'duplicates']+=1
        except (ValueError,KeyError,IntegrityError) as exc:
            if policy=='atomic':raise
            result['rejected'].append({'row':number,'reason':'integrity' if isinstance(exc,IntegrityError) else 'invalid_input'})
    return result
