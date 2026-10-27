from pathlib import Path
import base64,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.deployment_lab import deployed,request

def scenario(lab):
    seed(lab)
    with deployed(lab) as app:
        base=app['base'];ids=app['ids'];tokens=app['tokens']
        def send(path,who='reporter',body=None,method='GET',expected=200):
            status,data=request(base,path,tokens.get(who),body,method)
            check(status==expected,f'Deployed HTTP {method} {path.split("/")[1]} returns the expected status.')
            return data
        check(request(base,'/health/ready')[0]==200,'Fresh Compose services become healthy only after owner migrations and runtime database readiness.')
        ticket=send('/tickets',body=dict(asset_id=ids['asset'],title='Deployment repair',description='Synthetic HTTP acceptance'),method='POST',expected=201)['id']
        send('/tickets/'+ticket+'/transitions','admin',dict(action='assign',technician_id=ids['tech']),method='POST')
        order=send('/tickets/'+ticket+'/work-orders','tech',{},method='POST',expected=201)['id']
        send('/work-orders/'+order,'tech',dict(labor_cost='5.00',completion_note='Verified deployment repair'),method='PATCH')
        send('/work_order/'+order+'/attachments','tech',dict(filename='proof.bin',content_type='application/octet-stream',data_base64=base64.b64encode(b'synthetic proof').decode()),method='POST',expected=201)
        send('/work-orders/'+order+'/start','tech',{},method='POST')
        result=send('/work-orders/'+order+'/complete','tech',{},method='POST')
        check(result['total_cost']=='5.00','The containerized runtime completes a proof-backed repair with exact money.')
        send('/tickets/'+ticket+'/transitions','admin',dict(action='verify',reason='Deployment accepted'),method='POST')
        check(send('/reports/costs','admin')[0]['total_cost']=='5.00','Real network HTTP report agrees with the completed repair.')
        with app['engine'].connect() as c:
            check(c.scalar(text("SELECT count(*) FROM work_orders WHERE status='completed'"))==1,'Independent owner SQL observes the runtime HTTP commit.')
            check(c.scalar(text("SELECT rolname FROM pg_roles WHERE oid=(SELECT relowner FROM pg_class WHERE oid='assets'::regclass)"))=='college_owner','Application tables belong to the migration owner, not the runtime login.')
    check(lab.driver().execute('SELECT 1').fetchone()==(1,),'The existing learning database remains available after fresh deployment volumes are removed.')

if __name__=='__main__':run(62,scenario)
