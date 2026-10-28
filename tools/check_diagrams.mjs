/** Parse all concept-guide Mermaid blocks using ignored, optional local packages. */
import fs from 'node:fs';

const root = new URL('../', import.meta.url);
const modules = new URL('.local/doc-validation/node_modules/', root);
let JSDOM, mermaid;
try {
  ({ JSDOM } = await import(new URL('jsdom/lib/api.js', modules)));
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.DOMParser = dom.window.DOMParser;
  ({ default: mermaid } = await import(new URL('mermaid/dist/mermaid.esm.mjs', modules)));
} catch (error) {
  throw new Error('Install the optional local documentation packages as described in docs/DOCUMENTATION_VERIFICATION.md.', { cause: error });
}
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
const pages = ['README.md', 'docs/SQLALCHEMY.md', 'docs/POSTGRESQL.md',
  'docs/reference/SQLALCHEMY_APIS.md', 'docs/reference/POSTGRESQL_FUNCTIONS.md',
  'docs/reference/APPLICATION_FUNCTIONS.md'];
let count = 0;
for (const page of pages) {
  const text = fs.readFileSync(new URL(page, root), 'utf8');
  for (const match of text.matchAll(/^```mermaid\s*\n([\s\S]*?)^```/gm)) {
    await mermaid.parse(match[1]);
    count++;
  }
}
const version = JSON.parse(fs.readFileSync(new URL('mermaid/package.json', modules), 'utf8')).version;
console.log(`PASS: ${count} Mermaid diagrams across ${pages.length} pages; Mermaid ${version}.`);
