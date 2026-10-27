from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    seed(lab);root=Path(__file__).resolve().parents[2]
    args=['docker','compose','--file',str(root/'compose.yaml'),'exec','-T','--user','postgres','postgres','sh','/labs/step-78/recovery.sh',lab.run_id.hex]
    try:
        result=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=300)
        print(result.stdout)
        if result.returncode:raise RuntimeError('Recovery lab failed: '+result.stderr[-3000:])
        check(result.stdout.count('PASS:')==9,'Physical backup, archived-WAL PITR, physical replication and logical replication all execute rather than being configuration-only examples.')
    finally:
        cleanup=subprocess.run(args+['cleanup'],cwd=root,capture_output=True,text=True,timeout=90)
        if cleanup.returncode:raise RuntimeError('Scratch recovery cleanup failed: '+cleanup.stderr[-1500:])
    check(lab.driver().execute('SELECT current_database(),current_user').fetchone()==('college_learning','college_learner'),'The existing learning cluster remains available and unmodified by separate Unix-socket-only operations labs.')
    print('Recovery policy: observed RPO is the selected restore point; RTO is measured operational work, not a promised SLA. Replicas also receive unwanted changes and do not replace independently recoverable backups. Scratch trust authentication is restricted to a private container-local socket directory; no recovery port is published.')

if __name__=='__main__':run(78,scenario)
