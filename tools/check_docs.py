"""Check the concept guides/references without importing the app or using a database."""
from __future__ import annotations

import ast
from pathlib import Path
import re
from urllib.parse import unquote

import build_reference

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['README.md', 'docs/SQLALCHEMY.md', 'docs/POSTGRESQL.md',
         'docs/reference/SQLALCHEMY_APIS.md', 'docs/reference/POSTGRESQL_FUNCTIONS.md',
         'docs/reference/APPLICATION_FUNCTIONS.md', 'docs/DOCUMENTATION_VERIFICATION.md']


def headings(path):
    """GitHub-style anchors used by these plain-text headings (including duplicates)."""
    seen, anchors = {}, set()
    text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        title = re.sub(r'[`*_]', '', title).lower()
        slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
        count = seen.get(slug, 0)
        anchors.add(slug + (f'-{count}' if count else ''))
        seen[slug] = count + 1
    return anchors


def main():
    errors, links, diagrams, definitions = [], 0, 0, 0
    source = {name: (ROOT / name).read_text(encoding='utf-8') for name in PAGES}
    for name, text in source.items():
        page = ROOT / name
        if len(re.findall(r'^```', text, re.M)) % 2:
            errors.append(f'{name}: unbalanced code fence')
        diagrams += len(re.findall(r'^```mermaid\s*$', text, re.M))
        # Validate example syntax, including the explicitly shortened mapping.
        for code in re.findall(r'^```python\s*\n(.*?)^```', text, re.M | re.S):
            try:
                ast.parse(code)
            except SyntaxError as exc:
                errors.append(f'{name}: Python example: {exc}')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            if re.match(r'^[a-zA-Z]+:', target):
                continue
            links += 1
            relative, _, anchor = unquote(target).partition('#')
            path = (page.parent / relative).resolve() if relative else page
            if not path.is_relative_to(ROOT) or not path.exists():
                errors.append(f'{name}: missing/outside path {target}')
            elif anchor and path.is_file():
                if re.fullmatch(r'L\d+', anchor):
                    if not 1 <= int(anchor[1:]) <= len(path.read_text(encoding='utf-8-sig').splitlines()):
                        errors.append(f'{name}: source line out of bounds: {target}')
                elif path.suffix == '.md' and anchor not in headings(path):
                    errors.append(f'{name}: missing heading: {target}')
    _, _, _, _, _, functions = build_reference.inventory()
    located = {(p, n.lineno) for p, _, n in functions}
    for path in sorted((ROOT / 'college_maintenance').glob('*.py')):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions += 1
                if (path, node.lineno) not in located:
                    errors.append(f'Unindexed definition: {path.name}:{node.lineno}')
    # Each scanned definition must also appear as a real table source link.
    app_page = source['docs/reference/APPLICATION_FUNCTIONS.md']
    for path, _, node in functions:
        target = f'../../{path.relative_to(ROOT).as_posix()}#L{node.lineno}'
        if target not in app_page:
            errors.append(f'Missing rendered definition: {target}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(PAGES)} concept/reference pages; {links} local links/anchors; '
          f'{definitions} core function definitions covered; Python examples parse; '
          f'{diagrams} Mermaid blocks found (use Mermaid parser separately).')


if __name__ == '__main__':
    main()
