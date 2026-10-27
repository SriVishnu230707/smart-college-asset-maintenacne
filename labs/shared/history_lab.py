"""Install the exact reviewed history guards in an isolated study namespace."""
import importlib.util
from pathlib import Path
import re
from sqlalchemy import text

def install_guards(lab):
    spec=importlib.util.spec_from_file_location('frozen_history_revision',Path(__file__).resolve().parents[2]/'migrations/versions/0010_history_guards.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if not re.fullmatch(r'college_step(?:2[1-9]|[3-7][0-9]|80)',lab.schema):raise ValueError('Unexpected history study schema')
    # Published migration validation stays frozen. Replay its public-qualified
    # DDL through a narrowly scoped adapter instead of editing old revisions.
    with lab.engine.begin() as connection:
        class StudyDDL:
            def execute(self,statement):return connection.execute(text(str(statement).replace('public.',lab.schema+'.')))
            def exec_driver_sql(self,statement):return connection.exec_driver_sql(statement.replace('public.',lab.schema+'.'))
        module.install(StudyDDL())
