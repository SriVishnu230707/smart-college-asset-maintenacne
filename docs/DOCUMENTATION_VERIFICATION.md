# Documentation verification

[Project overview](../README.md) · [SQLAlchemy](SQLALCHEMY.md) · [PostgreSQL](POSTGRESQL.md)

This documentation update replaces step-by-step primary navigation with a project overview, two concept guides, and three source-linked indexes. The original learning checklist, evidence, application code, and migration history are retained.

## Coverage and checks

| Check | What it establishes |
|---|---|
| Reference regeneration | The checked-in indexes match the scanner and reviewed explanations. |
| Core AST coverage | Every one of the 130 core Python function definitions has a rendered source link, including nested helpers and HTTP handlers. |
| Library vocabulary | 98 distinct SQLAlchemy/Alembic import/reference names and 114 observed method names have explanations and examples. |
| Database vocabulary | 87 observed PostgreSQL function/routine/expression names and 46 SQL command forms have explanations and examples. |
| Local links | Guide/reference file targets, Markdown heading anchors, and source line bounds are checked. |
| Python examples | All Python code blocks in the concept guides parse without a syntax error. The mapping is explicitly shortened; the read example requires an authenticated actor. |
| Mermaid syntax | All 14 diagram blocks parse with Mermaid 12.2.0 in a JSDOM 29.1.1 environment. They use GitHub's native Mermaid Markdown blocks. Parsing verifies syntax; GitHub controls the final layout. |
| Git whitespace | `git diff --check` passes. |

These are documentation checks. They do not claim to re-execute the backend or to infer every dynamic Python/SQL call. The [source scanner](../tools/build_reference.py) documents its scope; human-reviewed definitions live in [reference_data.py](../tools/reference_data.py). The previous full application regression evidence remains linked from the overview.

## Reproduce

The Python checks use the project's existing virtual environment and standard library:

```powershell
.\.venv\Scripts\python.exe tools\build_reference.py --check
.\.venv\Scripts\python.exe tools\check_docs.py
git diff --check
```

To refresh the indexes after a source/glossary change:

```powershell
.\.venv\Scripts\python.exe tools\build_reference.py
```

Diagram syntax checking additionally uses Node.js (verified with 22.17.0). Its optional packages stay in ignored `.local/` and do not change the application dependencies:

```powershell
npm install --prefix .local/doc-validation --no-audit --no-fund --ignore-scripts mermaid@12.2.0 jsdom@29.1.1
node tools/check_diagrams.mjs
```

The commands above were run on 28 October 2026. Captured results for PowerShell 7 and Windows PowerShell 5.1 are in [documentation evidence](../tests/docs-evidence.txt).
