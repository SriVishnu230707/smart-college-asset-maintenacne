"""Real custom-format dump/restore, into an exact generated scratch database."""
from contextlib import contextmanager
from pathlib import Path
import subprocess
from labs.shared.operations_lab import scratch_database

@contextmanager
def restored_database(lab,step=63):
    root=Path(__file__).resolve().parents[2]
    with scratch_database(step,lab.run_id) as restored:
        def command(mode):
            args=['docker','compose','--file',str(root/'compose.yaml'),'exec','-T','postgres','sh','/labs/shared/backup.sh',mode,lab.schema,restored.url.database,lab.run_id.hex]
            result=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=120)
            if result.returncode:raise RuntimeError('Backup operation failed: '+result.stderr[-2000:])
        try:
            command('dump');command('restore')
            yield restored.execution_options(schema_translate_map={None:lab.schema})
        finally:command('cleanup')
