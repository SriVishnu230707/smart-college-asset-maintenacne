// Exercise the shipped script with controlled network timing, without a browser
// or dependencies. This is a small DOM fixture, not a substitute for HTTP tests.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../college_maintenance/static/app.js'), 'utf8');

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve: body => resolve({ ok: true, status: 200, json: async () => body }) };
}

function fixture(fetch) {
  const nodes = new Map();
  function node(selector) {
    if (!nodes.has(selector)) {
      const listeners = new Map();
      const element = {
        value: '', textContent: '', innerHTML: '', disabled: false, open: false,
        classList: { add() {}, remove() {}, toggle() {} },
        setAttribute() {}, removeAttribute() {}, replaceChildren() { this.innerHTML = ''; }, reset() {},
        addEventListener(name, callback) { listeners.set(name, callback); },
        showModal() { this.open = true; },
        close() { this.open = false; listeners.get('close')?.(); },
        querySelector(child) { return node(selector + ' ' + child); },
        querySelectorAll(child) {
          if (child !== 'form') return [];
          return [...nodes.entries()].filter(([name]) => name.endsWith('-form') && (
            selector === '#connect-dialog' && name === '#connect-form' ||
            selector === '#report-dialog' && name === '#report-form' ||
            selector === '#ticket-dialog' && ['#comment-form', '#transition-form'].includes(name)
          )).map(([, value]) => value);
        },
      };
      nodes.set(selector, element);
    }
    return nodes.get(selector);
  }
  const document = {
    querySelector: node,
    querySelectorAll(selector) {
      if (selector === 'dialog' || selector === 'dialog[open]') return ['#connect-dialog', '#report-dialog', '#ticket-dialog'].map(node).filter(value => selector === 'dialog' || value.open);
      return [];
    },
  };
  const context = vm.createContext({ document, fetch, AbortController, setTimeout, clearTimeout, URLSearchParams, Intl });
  vm.runInContext(source, context);
  const run = code => vm.runInContext(code, context);
  const signedIn = () => run("state.token='same-token';state.user={id:'student',name:'Student',role:'student',department:'CSE'}");
  const submit = selector => node(selector).onsubmit({ preventDefault() {}, currentTarget: node(selector) });
  return { node, run, signedIn, submit };
}

test('an older asset search cannot replace the latest search results', async () => {
  const first = deferred(); const second = deferred(); let calls = 0;
  const ui = fixture(() => (++calls === 1 ? first.promise : second.promise));
  ui.signedIn(); ui.node('#report-dialog').showModal();
  const old = ui.run('loadAssets()'); const current = ui.run('loadAssets()');
  second.resolve({ items: [{ id: 'new', asset_code: 'NEW', name: 'New result', status: 'active' }], next_offset: null });
  await current;
  first.resolve({ items: [{ id: 'old', asset_code: 'OLD', name: 'Old result', status: 'active' }], next_offset: null });
  await old;
  assert.match(ui.node('#report-asset').innerHTML, /New result/);
  assert.doesNotMatch(ui.node('#report-asset').innerHTML, /Old result/);
});

test('an asset request finishing after the report dialog closes is discarded', async () => {
  const request = deferred(); const ui = fixture(() => request.promise);
  ui.signedIn(); ui.node('#report-dialog').showModal();
  const pending = ui.run('loadAssets()'); ui.node('#report-dialog').close();
  request.resolve({ items: [{ id: 'late', asset_code: 'LATE', name: 'Late result', status: 'active' }], next_offset: null });
  await pending;
  assert.doesNotMatch(ui.node('#report-asset').innerHTML, /Late result/);
});

test('retired-only asset matches explain that no reportable assets are available', async () => {
  const request = deferred(); const ui = fixture(() => request.promise);
  ui.signedIn(); ui.node('#report-dialog').showModal();
  const pending = ui.run('loadAssets()');
  request.resolve({ items: [{ id: 'retired', name: 'Old computer', status: 'retired' }], next_offset: null });
  await pending;
  assert.match(ui.node('#asset-hint').textContent, /No reportable assets/);
});

test('disconnect and reconnect with the same token invalidates earlier responses', async () => {
  const request = deferred(); const ui = fixture(() => request.promise);
  ui.signedIn();
  const pending = ui.run("api('/me')");
  ui.run('disconnect()'); ui.signedIn(); request.resolve({ name: 'Old response' });
  await assert.rejects(pending, /connection changed/i);
});

test('cancelled sign-in cannot reconnect the account when its response arrives', async () => {
  const request = deferred();
  const ui = fixture(path => path === '/me' ? request.promise : Promise.resolve({ ok: true, status: 200, json: async () => path === '/dashboard/summary' ? {} : { items: [] } }));
  ui.node('#connect-dialog').showModal(); ui.node('#token').value = 'test-token';
  const pending = ui.submit('#connect-form'); ui.node('#connect-dialog').close();
  request.resolve({ id: 'student', name: 'Student', role: 'student', department: 'CSE' });
  await pending;
  assert.equal(ui.run('state.user'), null);
  assert.equal(ui.run('state.token'), '');
  assert.equal(ui.node('#connect-form button[type="submit"], button:not([type])').disabled, false);
});

test('a delayed comment response does not reopen a closed ticket', async () => {
  const mutation = deferred();
  const ui = fixture((path, options) => options.method === 'POST' ? mutation.promise : Promise.resolve({ ok: true, status: 200, json: async () => path.endsWith('/comments') ? [] : { id: 'ticket-a', title: 'Issue', description: 'Details', status: 'open', priority: 'medium' } }));
  ui.signedIn(); await ui.run("openTicket('ticket-a')");
  ui.node('#comment-body').value = 'Helpful update';
  const pending = ui.submit('#comment-form'); ui.node('#ticket-dialog').close();
  mutation.resolve({ id: 'comment' }); await pending;
  assert.equal(ui.node('#ticket-dialog').open, false);
});

test('a cancelled sign-in response cannot clear a newer successful connection', async () => {
  const old = deferred(); const current = deferred(); let attempts = 0;
  const ui = fixture(path => path === '/me' ? (++attempts === 1 ? old.promise : current.promise) : Promise.resolve({ ok: true, status: 200, json: async () => path === '/dashboard/summary' ? {} : { items: [] } }));
  ui.node('#connect-dialog').showModal(); ui.node('#token').value = 'old-token';
  const earlier = ui.submit('#connect-form'); ui.node('#connect-dialog').close();
  ui.node('#connect-dialog').showModal(); ui.node('#token').value = 'new-token';
  const latest = ui.submit('#connect-form');
  current.resolve({ id: 'new-student', name: 'New Student', role: 'student', department: 'ECE' });
  await latest; old.resolve({ id: 'old-student', name: 'Old Student', role: 'student', department: 'CSE' });
  await earlier;
  assert.equal(ui.run('state.user.id'), 'new-student');
  assert.equal(ui.run('state.token'), 'new-token');
  assert.equal(ui.node('#user-name').textContent, 'New Student');
});

test('a cancelled report response cannot close or reset a reopened report form', async () => {
  const request = deferred(); const ui = fixture(() => request.promise);
  ui.signedIn(); ui.node('#report-dialog').showModal();
  ui.node('#report-subject').value = 'Original issue'; ui.node('#report-description').value = 'Description';
  const pending = ui.submit('#report-form'); ui.node('#report-dialog').close();
  ui.node('#report-dialog').showModal(); ui.node('#report-subject').value = 'New draft';
  request.resolve({ id: 'created-ticket' }); await pending;
  assert.equal(ui.node('#report-dialog').open, true);
  assert.equal(ui.node('#report-subject').value, 'New draft');
});
