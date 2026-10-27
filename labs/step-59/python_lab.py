from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.integration_cases import suite
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab)
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite(lab,ids))
    check(result.testsRun==8 and result.wasSuccessful(),'Eight real PostgreSQL integration cases pass, including independent-backend contention and HTTP authorization.')
    check(not result.skipped,'No integration behavior was silently skipped or substituted with SQLite.')
    check(lab.driver().execute(f'SELECT count(*) FROM {lab.schema}.maintenance_tickets').fetchone()[0]==1,'Independent committed visibility confirms the HTTP case persisted exactly one ticket.')
    print('Fixture policy: ordinary isolation may use rollback; real commit/visibility and locks require distinct backend connections. Earlier labs retain full migration, completion-failure and idempotency cases in tests/run.ps1.')

if __name__=='__main__':run(59,scenario)
