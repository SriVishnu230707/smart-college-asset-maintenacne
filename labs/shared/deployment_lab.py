"""Fresh Compose projects; cleanup targets only resources created by this run."""
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime,timedelta,timezone
import hashlib,json,os,secrets,subprocess
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from labs.shared.orm_lab import Lab
from labs.shared.workflow_lab import seed

ROOT=Path(__file__).resolve().parents[2]

def request(base,path,token=None,body=None,method='GET'):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    data=None if body is None else json.dumps(body,default=str).encode()
    try:
        with urlopen(Request(base+path,data=data,headers=headers,method=method),timeout=15) as response:return response.status,json.load(response)
    except HTTPError as error:return error.code,json.loads(error.read())

@contextmanager
def deployed(lab):
    name='college-step62-'+lab.run_id.hex[:12]
    directory=ROOT/'.local'/name;directory.mkdir()
    password=secrets.token_urlsafe(32);owner_pw=secrets.token_urlsafe(32);runtime_pw=secrets.token_urlsafe(32)
    urls={key:URL.create('postgresql+psycopg',username=user,password=pw,host='postgres',database='college_deploy') for key,user,pw in [('admin_url','postgres',password),('owner_url','college_owner',owner_pw),('runtime_url','college_runtime',runtime_pw)]}
    for key,url in urls.items():(directory/key).write_text(url.render_as_string(hide_password=False),encoding='utf-8')
    (directory/'postgres_password').write_text(password,encoding='utf-8');(directory/'api_tokens').write_text('{}',encoding='utf-8')
    env={**os.environ,'COLLEGE_DEPLOY_SECRETS':str(directory)}
    args=['docker','compose','--project-name',name,'--file',str(ROOT/'compose.deploy.yaml')]
    def command(*values,timeout=600):
        result=subprocess.run(args+list(values),cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        if result.returncode:raise RuntimeError('Compose operation failed: '+result.stdout[-2500:]+result.stderr[-5000:])
        return result.stdout.strip()
    target=None
    try:
        command('up','--build','--detach','--wait','--wait-timeout','180','api')
        port=int(command('port','postgres','5432').rsplit(':',1)[1]);api_port=int(command('port','api','8000').rsplit(':',1)[1])
        target=create_engine(urls['owner_url'].set(host='127.0.0.1',port=port),hide_parameters=True)
        class Fixture:
            engine=target
            session=sessionmaker(bind=target)
            def seed(self):return Lab.seed(self)
        ids=seed(Fixture());tokens={key:secrets.token_urlsafe(32) for key in ids if key in {'reporter','tech','admin','super','other_admin'}}
        expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        entries={hashlib.sha256(token.encode()).hexdigest():{'actor_id':str(ids[key]),'expires_at':expires} for key,token in tokens.items()}
        (directory/'api_tokens').write_text(json.dumps(entries),encoding='utf-8')
        yield dict(base=f'http://127.0.0.1:{api_port}',engine=target,ids=ids,tokens=tokens,command=command,directory=directory)
    finally:
        if target:target.dispose()
        # Explicit fresh project name; never targets college-maintenance-lab.
        command('down','--volumes','--remove-orphans',timeout=120)
