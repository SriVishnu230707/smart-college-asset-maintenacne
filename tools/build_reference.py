"""Build/check offline, source-linked Markdown references using only the stdlib.

Usage: python tools/build_reference.py [--check]
Scope: tracked-style source trees, not installed packages or generated evidence.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path
import re

from reference_data import APPLICATION, LIBRARY, METHODS, POSTGRES, PURPOSES

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs' / 'reference'
SOURCE_ROOTS = ('college_maintenance', 'labs', 'migrations', 'tests', 'docker')


def source_files():
    return sorted(p for root in SOURCE_ROOTS for p in (ROOT / root).rglob('*')
                  if p.is_file() and p.suffix in {'.py', '.sql', '.sh', '.ps1'}
                  and '__pycache__' not in p.parts)


def location(path, line):
    return path.relative_to(ROOT).as_posix(), line


def link(loc):
    path, line = loc
    label = path.removeprefix('college_maintenance/') if path.startswith('college_maintenance/') else path.replace('python_lab.py', 'Python').replace('verify.sql', 'SQL')
    return f'[{label}:{line}](../../{path}#L{line})'


def examples(locations):
    ordered = sorted(set(locations), key=lambda loc: (not loc[0].startswith('college_maintenance/'), loc))
    # One core use plus up to two other source files keeps the index scannable.
    seen, picked = set(), []
    for loc in ordered:
        if loc[0] not in seen:
            picked.append(link(loc))
            seen.add(loc[0])
        if len(picked) == 3:
            break
    return '<br/>'.join(picked)


def table_sections(rows, labels, level=2):
    sections = []
    for group in dict.fromkeys(row[0] for row in rows):
        sections.extend([f'{"#" * level} {group}', '', '| ' + ' | '.join(labels) + ' |',
                         '|' + '|'.join('---' for _ in labels) + '|'])
        for row in sorted((r for r in rows if r[0] == group), key=lambda r: r[1].lower()):
            sections.append('| ' + ' | '.join(str(cell).replace('|', r'\|').replace('\n', ' ') for cell in row[1:]) + ' |')
        sections.append('')
    return '\n'.join(sections)


def sql_fragments(path, text, tree):
    if tree is None:
        yield text, 1
        return
    # Literal SQL can be passed to text()/execute(), assembled in f-strings,
    # or embedded in constraint/migration definitions. Never import application code.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value, node.lineno
        elif isinstance(node, ast.JoinedStr):
            yield ''.join(n.value if isinstance(n, ast.Constant) and isinstance(n.value, str)
                          else 'DYNAMIC' for n in node.values), node.lineno


def plausible_method(node, method, text):
    """Conservative example selection, not a Python type checker.

    Ambiguous Python/HTTP/psycopg calls are excluded. Unique builder/inspection
    names can use chained expressions; common names require a SQLAlchemy receiver.
    """
    receiver = ast.unparse(node.func.value)
    root = receiver.split('.', 1)[0].split('(', 1)[0]
    if root in {'app', 'client', 'store', 'data', 'body', 'payload', 'os', 'file',
                'Path', 'path', 'self', 'datetime', 'hashlib', 'json', 're', 'row',
                'mapping', 'headers', 'response', 'values', 'kwargs', 'environment'}:
        return False
    common = {'get', 'delete', 'add', 'close', 'begin', 'connect', 'commit', 'rollback',
              'execute', 'scalar', 'first', 'all', 'keys', 'fetchone', 'fetchall',
              'join', 'contains', 'create', 'set', 'remove', 'size', 'configure'}
    if method not in common:
        return True
    if re.fullmatch(r'(?:conn(?:ection)?|c|db)', root):
        # A raw driver connection has the same method names. Prefer explicit
        # Engine context examples only; other examples remain in the source.
        return bool(re.search(rf'with\s+\w+\.(?:begin|connect)\(\)\s+as\s+{root}\b', text))
    return bool(re.match(r'(?:session|s\d*$|engine|eng$|result|res$|rows$|stmt|statement|query|q$|'
                         r'url|cfg|config|context|op$|command|event|metadata|inspector|ins$|'
                         r'table|select|insert|update|delete|func|inspect|[A-Z])', root))


def inventory():
    symbols, methods, functions, commands, clients = (defaultdict(list) for _ in range(5))
    application = []
    for path in source_files():
        text = path.read_text(encoding='utf-8-sig')
        tree = ast.parse(text, filename=str(path)) if path.suffix == '.py' else None
        aliases = {}
        if tree:
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and (n.module or '').startswith(('sqlalchemy', 'alembic')):
                    for alias in n.names:
                        full = f'{n.module}.{alias.name}'
                        aliases[alias.asname or alias.name] = full
                        symbols[full].append(location(path, n.lineno))
                elif isinstance(n, ast.Import):
                    for alias in n.names:
                        if alias.name.startswith(('sqlalchemy', 'alembic')):
                            aliases[alias.asname or alias.name] = alias.name
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                    base = aliases.get(n.value.id, '')
                    if base and n.attr in LIBRARY:
                        symbols[f'{base}.{n.attr}'].append(location(path, n.lineno))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                    expr = ast.unparse(n.func)
                    if re.search(r'(?:^|\.)func\.\w+$', expr):
                        functions[n.func.attr.lower()].append(location(path, n.lineno))
                    elif aliases and n.func.attr in METHODS and plausible_method(n, n.func.attr, text):
                        methods[n.func.attr].append(location(path, n.func.end_lineno or n.lineno))
            if path.parent == ROOT / 'college_maintenance':
                def walk(parent, scope=''):
                    for n in ast.iter_child_nodes(parent):
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            qualified = scope + n.name
                            if not isinstance(n, ast.ClassDef):
                                application.append((path, qualified, n))
                            walk(n, qualified + '.')
                        else:
                            walk(n, scope)
                walk(tree)
        for fragment, start_line in sql_fragments(path, text, tree):
            # SQL comments are not function calls; retain newlines for anchors.
            fragment = re.sub(r'--[^\n]*', '', fragment)
            for name in POSTGRES:
                pattern = rf'(?<!\w){re.escape(name)}\s*\('
                if name == 'current_user':
                    pattern = r'\bcurrent_user\b'
                for match in re.finditer(pattern, fragment, re.I):
                    functions[name].append(location(path, start_line + fragment[:match.start()].count('\n')))
            # This allowlist covers actual SQL commands used by the project;
            # syntax/operators receive a separate explanation below the tables.
            for match in re.finditer(r'\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?(?:MATERIALIZED\s+VIEW|TABLE|SCHEMA|DATABASE|ROLE|DOMAIN|TYPE|FUNCTION|TRIGGER|VIEW|INDEX|POLICY|PUBLICATION|SUBSCRIPTION)|ALTER\s+(?:TABLE|SCHEMA|DATABASE|ROLE|DOMAIN|TYPE|SEQUENCE|SUBSCRIPTION)|DROP\s+(?:MATERIALIZED\s+VIEW|TABLE|SCHEMA|DATABASE|ROLE|DOMAIN|TYPE|FUNCTION|TRIGGER|VIEW|INDEX|POLICY|PUBLICATION|SUBSCRIPTION)|SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|TRUNCATE|GRANT|REVOKE|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE\s+SAVEPOINT|SET|SHOW|DO|COPY|VACUUM|ANALYZE|EXPLAIN|REFRESH\s+MATERIALIZED\s+VIEW)\b', fragment, re.I):
                # Avoid prose in error strings and ordinary Python literals.
                if not re.search(r'\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|GRANT|REVOKE|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|SET|SHOW|DO|COPY|VACUUM|ANALYZE|EXPLAIN|REFRESH|TRUNCATE)\b', fragment):
                    continue
                name = re.sub(r'\s+', ' ', match.group().upper()).replace('OR REPLACE ', '').replace('UNIQUE INDEX', 'INDEX')
                commands[name].append(location(path, start_line + fragment[:match.start()].count('\n')))
        if path.suffix in {'.sh', '.ps1'}:
            for name in ('psql', 'pg_dump', 'pg_restore', 'pg_basebackup', 'pg_ctl', 'initdb', 'pg_isready'):
                for match in re.finditer(rf'\b{re.escape(name)}\b', text):
                    clients[name].append(location(path, 1 + text[:match.start()].count('\n')))
    return symbols, methods, functions, commands, clients, application


def sqlalchemy_page(symbols, methods):
    rows = []
    for full, locs in symbols.items():
        name = full.rsplit('.', 1)[-1]
        if name not in LIBRARY:
            raise ValueError(f'Add a reviewed library explanation for {full}')
        group, meaning = LIBRARY[name]
        rows.append((group, f'`{name}`', meaning + f'<br/>Import: `{full}`', examples(locs)))
    intro = f'''# SQLAlchemy and Alembic API index

[Overview](../../README.md) · [SQLAlchemy explained](../SQLALCHEMY.md) · [Application functions](APPLICATION_FUNCTIONS.md)

This page explains **{len(symbols)} distinct imported/referenced library symbols** and **{len(methods)} observed method names**. A symbol may be a class, annotation, namespace, exception, decorator, or function. Import rows identify names available to a module; an import alone does not prove runtime execution.

The offline scanner reads Python under `college_maintenance/`, `labs/`, `migrations/`, and `tests/`. It resolves direct SQLAlchemy/Alembic imports and known namespace attributes. Method rows use a reviewed vocabulary and conservative receiver filtering, with representative source locations; this is a navigation aid, not full Python type inference. Dynamic calls and installed-library internals are outside this index. A source link in `labs/` denotes an isolated experiment, not an enabled application feature.

```mermaid
flowchart LR
    Map["Models and types"] --> Build["Statement builders"]
    Build --> Execute["Engine / Connection / Session"]
    Execute --> Consume["Result consumption"]
    Inspect["Inspection and migrations"] --> Map
    Load["Relationship loaders"] --> Execute
```

## Imported and namespace-referenced symbols

'''
    method_rows = [(METHODS[name][0], f'`.{name}()`', METHODS[name][1], examples(locs))
                   for name, locs in methods.items()]
    return (intro + table_sections(rows, ('Symbol', 'Meaning', 'Source examples'), level=3)
            + '\n## Methods\n\n' + table_sections(method_rows, ('Method', 'Meaning', 'Source examples'), level=3))


def postgres_page(functions, commands, clients):
    rows = []
    for name, locs in functions.items():
        if name not in POSTGRES:
            raise ValueError(f'Add a reviewed PostgreSQL explanation for func.{name}')
        group, meaning = POSTGRES[name]
        if name in {'lower', 'upper'}:
            meaning += ' With a range input, return the lower/upper bound instead.'
        rows.append((group, f'`{name}`', meaning, examples(locs)))
    intro = f'''# PostgreSQL function and command index

[Overview](../../README.md) · [PostgreSQL explained](../POSTGRESQL.md) · [SQLAlchemy APIs](SQLALCHEMY_APIS.md)

The tables identify **{len(functions)} observed function/routine/expression names** and **{len(commands)} SQL command forms**, with source examples. Ordinary functions, special SQL expressions, repository-defined routines, and client programs are separated so their responsibilities are clear.

Scope: literal SQL and SQL f-string fragments in Python, SQL, shell, and PowerShell sources under `college_maintenance/`, `labs/`, `migrations/`, `tests/`, and `docker/`, plus Python `func.NAME(...)` calls. A reviewed vocabulary excludes types, table names, and Python methods that resemble SQL calls. Dynamically assembled identifiers and operators cannot be exhaustively inferred this way; see their source and the [PostgreSQL 18 manual](https://www.postgresql.org/docs/18/functions.html). The full core Python definition inventory is on the [application function page](APPLICATION_FUNCTIONS.md).

```mermaid
flowchart TD
    SQL["A SQL statement"] --> Values["Functions and expressions<br/>Calculate values"]
    SQL --> Shape["Clauses and operators<br/>Choose / combine rows"]
    SQL --> Commands["Commands<br/>Change data, schema or server state"]
    Values --> Builtin["PostgreSQL built-ins"]
    Values --> Custom["Project-defined routines"]
    Client["psql / backup tools"] --> SQL
```

'''
    descriptions = {
        'SELECT': 'Read/project rows; joins, grouping, windows, and subqueries shape the answer.',
        'INSERT INTO': 'Insert records; conflict handling and RETURNING may modify its behavior.',
        'UPDATE': 'Change qualifying records; predicates can enforce stock/version guards.',
        'DELETE FROM': 'Remove qualifying records subject to constraints and history guards.',
        'TRUNCATE': 'Empty tables under stronger table locks in controlled fixtures.',
        'GRANT': 'Assign database privileges or role membership.', 'REVOKE': 'Remove privileges or role membership.',
        'BEGIN': 'Start a transaction.', 'COMMIT': 'Commit transaction changes.', 'ROLLBACK': 'Discard transaction changes, optionally to a savepoint.',
        'SAVEPOINT': 'Mark a recoverable point inside the transaction.', 'RELEASE SAVEPOINT': 'Release a savepoint while keeping the outer transaction open.',
        'SET': 'Change session/transaction configuration or the effective role.', 'SHOW': 'Read a configuration setting.',
        'DO': 'Execute an anonymous procedural block, including SQL assertions.',
        'COPY': 'Stream rows between PostgreSQL and a client/file; driver copy methods use this protocol.',
        'VACUUM': 'Reclaim reusable dead-row space and maintain visibility information.',
        'ANALYZE': 'Update column statistics used by the query planner.',
        'EXPLAIN': 'Inspect the plan; ANALYZE actually executes the statement and adds measured timings/rows.',
        'REFRESH MATERIALIZED VIEW': 'Recompute the stored rows of a materialized view.',
    }
    command_rows = []
    for name, locs in commands.items():
        if name.startswith(('CREATE ', 'ALTER ', 'DROP ')):
            verb, obj = name.split(' ', 1)
            meaning = f'{dict(CREATE="Define", ALTER="Change", DROP="Remove")[verb]} a {obj.lower()} in the database.'
            group = 'Schema, roles, and replication commands'
        else:
            meaning = descriptions[name]
            group = 'Data, transaction, and maintenance commands'
        command_rows.append((group, f'`{name}`', meaning, examples(locs)))
    client_meanings = {
        'psql': 'Run SQL and psql meta-commands in a command-line client.',
        'pg_dump': 'Create a logical database backup.', 'pg_restore': 'Restore a non-plain pg_dump archive.',
        'pg_basebackup': 'Copy a running cluster for a physical backup/standby.',
        'pg_ctl': 'Start, stop, or inspect a PostgreSQL server process.',
        'initdb': 'Initialize a new private PostgreSQL cluster.', 'pg_isready': 'Check whether a PostgreSQL server accepts connections.',
    }
    client_rows = [('Client programs', f'`{name}`', client_meanings[name], examples(locs)) for name, locs in clients.items()]
    return (intro + table_sections(rows, ('Name', 'Meaning', 'Source examples')) + '\n'
            + table_sections(command_rows, ('Command', 'Meaning', 'Source examples')) + '\n'
            + table_sections(client_rows, ('Program', 'Meaning', 'Source examples')) + '''
## Other SQL building blocks

| Construct | Meaning | Source |
|---|---|---|
| `CASE WHEN … THEN … ELSE … END` | Choose a value by conditions. | [model constraints](../../college_maintenance/models.py) |
| `JOIN`, `LEFT JOIN`, `LATERAL` | Combine row sources; lateral can use the preceding row. | [advanced reports](../../college_maintenance/advanced_reports.py) |
| `WITH`, recursive CTE | Name a query result or repeatedly traverse a hierarchy. | [recursive CTE](../../labs/step-67/python_lab.py), [report CTE](../../college_maintenance/advanced_reports.py) |
| `DISTINCT ON`, `ORDER BY`, `LIMIT`, `OFFSET` | Choose representatives and deterministic pages. | [reports](../../college_maintenance/advanced_reports.py), [pagination](../../college_maintenance/pagination.py) |
| `OVER (PARTITION BY … ORDER BY …)` | Calculate values over related rows without collapsing each group. | [analytics](../../college_maintenance/analytics.py) |
| `FILTER (WHERE …)`, `GROUP BY`, `HAVING` | Limit aggregate inputs, define groups, and filter grouped output. | [SQL reporting examples](../../labs/step-11/query.sql) |
| `UNION`, `INTERSECT`, `EXCEPT` | Combine, intersect, or subtract compatible result sets. | [set operations](../../labs/step-67/python_lab.py) |
| `IS NULL`, `IS NOT NULL`, `IN`, `ANY`, `ARRAY` | Null tests, membership, and collection expressions. | [type experiments](../../labs/step-72/python_lab.py) |
| `::`, `->`, `->>`, `@>`, `&&`, `@@` | PostgreSQL casts, JSON access, containment, overlap, and search operators. | [search](../../college_maintenance/search.py), [type experiments](../../labs/step-72/python_lab.py) |
| `FOR UPDATE`, `ON CONFLICT`, `RETURNING` | Coordinate writers, handle targeted duplicates, and obtain affected values. | [inventory](../../college_maintenance/inventory.py), [imports](../../college_maintenance/imports.py) |

`psycopg.connect()`, cursor `execute()`/`fetchone()`/`fetchall()`, `copy()`/`write_row()`, `commit()`/`rollback()`, and `psycopg.sql.SQL`/`Identifier`/`Literal` are Python driver APIs, not PostgreSQL server functions. See the [driver connection example](../../labs/step-13/python_lab.py) and [COPY comparison](../../labs/step-76/python_lab.py). SQLAlchemy methods are explained in their [own index](SQLALCHEMY_APIS.md).
''')


def app_page(application):
    sections = []
    for module, title in APPLICATION.items():
        sections.extend([f'## {title}', '', f'Module: [`{module}.py`](../../college_maintenance/{module}.py)', '',
                         '| Function / method | Purpose | Source |', '|---|---|---|'])
        for path, name, node in application:
            if path.stem != module:
                continue
            purpose = PURPOSES.get(f'{module}:{name}')
            routes = [d for d in node.decorator_list if isinstance(d, ast.Call) and
                      isinstance(d.func, ast.Attribute) and d.func.attr in {'get', 'post', 'patch', 'put', 'delete'}]
            if routes:
                route = routes[0]
                purpose = f'Handle **{route.func.attr.upper()} {ast.literal_eval(route.args[0])}**; validate dependencies, call the service, and return its response.'
                if name.endswith('.ready'):
                    purpose = 'Handle **GET /health/ready** by executing SELECT 1 through the configured Session.'
            if purpose is None:
                raise ValueError(f'Add an application explanation for {module}:{name}')
            args = node.args
            parameters = [a.arg for a in args.posonlyargs + args.args]
            if args.vararg:
                parameters.append('*' + args.vararg.arg)
            elif args.kwonlyargs:
                parameters.append('*')
            parameters.extend(a.arg for a in args.kwonlyargs)
            if args.kwarg:
                parameters.append('**' + args.kwarg.arg)
            signature = name + '(' + ', '.join(parameters) + ')'
            sections.append(f'| `{signature}` | {purpose} | {link(location(path, node.lineno))} |')
        sections.append('')
    unknown = {p.stem for p, _, _ in application} - APPLICATION.keys()
    if unknown:
        raise ValueError(f'Add application module groups: {unknown}')
    return f'''# Application function map

[Overview](../../README.md) · [SQLAlchemy explained](../SQLALCHEMY.md) · [PostgreSQL explained](../POSTGRESQL.md)

This source-derived inventory covers **all {len(application)} Python function definitions** in `college_maintenance/*.py`: public functions, private helpers, methods, nested dependencies, and route/error handlers. Type annotations/default values are omitted from signatures for readability; the source is authoritative. A name such as `create_app.get_ticket` describes lexical nesting, not an importable dotted path. Constructors generated by libraries/dataclasses, lab functions, and migration revision functions are outside this core definition inventory.

```mermaid
flowchart TD
    Auth["Authentication and HTTP routes"] --> Read["Authorized reads / pagination / search"]
    Auth --> Write["Ticket workflow / work orders"]
    Write --> Complete["Completion transaction"]
    Complete --> Stock["Inventory and movement ledger"]
    Complete --> Proof["Attachment verification"]
    Write --> Audit["Audit history"]
    Complete --> Audit
    Read --> Report["Reports and analytics"]
    Config["Engine / Sessions / migrations"] --> Read
    Config --> Write
```

Function names here belong to the project. [SQLAlchemy symbols/methods](SQLALCHEMY_APIS.md) and [PostgreSQL functions/commands](POSTGRESQL_FUNCTIONS.md) have separate indexes. Core code also contains optional prototypes such as `report_views`; inclusion here does not make them active HTTP features.

''' + '\n'.join(sections)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if a generated reference differs from source')
    args = parser.parse_args()
    symbols, methods, functions, commands, clients, application = inventory()
    outputs = {
        'SQLALCHEMY_APIS.md': sqlalchemy_page(symbols, methods),
        'POSTGRESQL_FUNCTIONS.md': postgres_page(functions, commands, clients),
        'APPLICATION_FUNCTIONS.md': app_page(application),
    }
    failures = []
    for name, content in outputs.items():
        content = content.rstrip() + '\n\n<!-- Generated by tools/build_reference.py; explanations: tools/reference_data.py. -->\n'
        path = DEST / name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                failures.append(path.relative_to(ROOT).as_posix())
        else:
            DEST.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8', newline='\n')
    if failures:
        raise SystemExit('Reference pages need regeneration: ' + ', '.join(failures))
    print(f'{"PASS" if args.check else "WROTE"}: 3 reference pages; '
          f'{len(symbols)} library symbols, {len(methods)} method names, '
          f'{len(functions)} SQL names, {len(commands)} command forms, '
          f'{len(application)} application definitions.')


if __name__ == '__main__':
    main()
