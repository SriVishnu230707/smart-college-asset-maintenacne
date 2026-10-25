"""Install the exact reviewed history guards in an isolated study namespace."""
import importlib.util
from pathlib import Path

def install_guards(lab):
    spec=importlib.util.spec_from_file_location('frozen_history_revision',Path(__file__).resolve().parents[2]/'migrations/versions/0010_history_guards.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with lab.engine.begin() as connection:module.install(connection,lab.schema)
