'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { token: '', user: null, view: 'overview', cursor: null, next: null, offset: 0, nextOffset: null, status: '', priority: '', assetSearch: '', revision: 0, detail: 0, session: 0, assetRequest: 0 };
const titles = { overview: ['Maintenance overview', 'A clearer view of what needs care across your campus.'], tickets: ['Maintenance tickets', 'Follow every issue, from the first report to the final fix.'], assets: ['Asset directory', 'Find the equipment and spaces that keep your campus moving.'], inventory: ['Spare parts', 'Check available stock and see what needs replenishing.'], reports: ['Maintenance reports', 'Understand repair costs and recurring equipment issues.'] };
const admin = () => ['department_admin', 'super_admin'].includes(state.user?.role);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const label = value => String(value ?? '').replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
const date = value => value ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) : '—';
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value));
const badge = (value, priority = false) => `<span class="badge ${escapeHTML(value)}">${priority ? '<span class="priority-dot"></span>' : ''}${escapeHTML(label(value))}</span>`;
const empty = (title, text) => `<div class="empty"><span class="empty-icon" aria-hidden="true">◇</span><h3>${escapeHTML(title)}</h3><p>${escapeHTML(text)}</p></div>`;
const panel = (title, subtitle, body, extra = '') => `<section class="panel"><div class="panel-heading"><div><h2>${escapeHTML(title)}</h2><p>${escapeHTML(subtitle)}</p></div>${extra}</div>${body}</section>`;

function notify(message, error = false) {
  const node = $('#notice'); node.textContent = message; node.hidden = !message; node.classList.toggle('error', error);
}
function disconnect(message = '') {
  state.token = ''; state.user = null; state.revision++; state.detail++; state.session++; state.assetRequest++;
  state.cursor = null; state.next = null; state.offset = 0; state.nextOffset = null;
  state.status = ''; state.priority = ''; state.assetSearch = '';
  $('#token').value = ''; $('#user-name').textContent = 'Guest workspace'; $('#user-role').textContent = 'Connect to get started';
  $('#avatar').textContent = '—'; $('#connection-button').textContent = 'Connect account'; $('#connection-state').textContent = 'Not connected';
  $('.topbar').classList.remove('connected'); $('#department').textContent = 'YOUR CAMPUS WORKSPACE';
  $$('[data-staff], [data-admin]').forEach(node => { node.hidden = true; });
  $('#mobile-account').textContent = 'Connect'; $('#content').removeAttribute('aria-busy');
  $$('dialog[open]').forEach(dialog => dialog.close()); $('#ticket-detail').replaceChildren(); $('#report-form').reset();
  $('#report-asset').innerHTML = '<option value="">Choose an asset</option>'; $('#asset-hint').textContent = '';
  $('#welcome').hidden = false; $('#content').replaceChildren(); setHeading('overview'); notify(message, Boolean(message));
}
async function api(path, options = {}) {
  const token = state.token; const session = state.session;
  if (!token) throw new Error('Connect your account to continue.');
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal, headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers }, cache: 'no-store' });
    const body = await response.json().catch(() => ({}));
    if (session !== state.session || token !== state.token) throw new Error('Your connection changed. Please try again.');
    if (response.status === 401) { if (state.user) disconnect('Your access token has expired or is invalid. Connect again to continue.'); else state.token = ''; throw new Error('Access token expired or invalid. Check the token and try again.'); }
    if (!response.ok) {
      const detail = Array.isArray(body.detail) ? body.detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join('; ') : body.detail;
      throw new Error(detail || `The request failed (${response.status}). Please try again.`);
    }
    return body;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The server took too long to respond. Please try again.');
    if (error instanceof TypeError) throw new Error('Unable to reach the server. Check your connection and try again.');
    throw error;
  } finally { clearTimeout(timer); }
}
const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) });
function setHeading(view) {
  state.view = view; $('#page-title').textContent = titles[view][0]; $('#page-subtitle').textContent = titles[view][1]; $('#breadcrumb').textContent = label(view);
  $$('[data-view]').forEach(button => { button.classList.toggle('active', button.dataset.view === view); if (button.dataset.view === view) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current'); });
}
function ticketTable(items) {
  if (!items.length) return empty('No tickets here yet', 'Try another filter, or report an issue to get started.');
  return `<div class="table-scroll"><table><caption>Maintenance tickets</caption><thead><tr><th scope="col">Issue / ticket</th><th scope="col">Status</th><th scope="col">Priority</th><th scope="col">Assigned to</th><th scope="col">Reported</th></tr></thead><tbody>${items.map(ticket => `<tr><td><button class="ticket-link" data-ticket="${escapeHTML(ticket.id)}">${escapeHTML(ticket.title)}<span class="ticket-code">#${escapeHTML(ticket.id.slice(0, 8).toUpperCase())}</span></button></td><td>${badge(ticket.status)}</td><td>${badge(ticket.priority, true)}</td><td>${escapeHTML(ticket.assignee_name || 'Unassigned')}</td><td>${escapeHTML(date(ticket.created_at))}</td></tr>`).join('')}</tbody></table></div>`;
}
function filters() {
  return `<form id="ticket-filters" class="filters"><select aria-label="Filter by status" id="status-filter"><option value="">All statuses</option>${['open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected'].map(value => `<option value="${value}" ${state.status === value ? 'selected' : ''}>${label(value)}</option>`).join('')}</select><select aria-label="Filter by priority" id="priority-filter"><option value="">All priorities</option>${['low', 'medium', 'high', 'critical'].map(value => `<option ${state.priority === value ? 'selected' : ''} value="${value}">${label(value)}</option>`).join('')}</select><button class="secondary">Apply filters</button></form>`;
}
async function render() {
  if (!state.user) return;
  const revision = ++state.revision; const view = state.view; $('#content').innerHTML = '<div class="loading" role="status">Loading your workspace…</div>'; $('#content').setAttribute('aria-busy', 'true');
  try {
    let html;
    if (view === 'overview') {
      const [summary, tickets] = await Promise.all([api('/dashboard/summary'), api('/tickets?limit=5')]);
      const cards = [['Active tickets', summary.active, 'Open and ongoing repairs', '☷'], ['High priority', summary.urgent, 'Active high & critical issues', '↗'], ['Awaiting verification', summary.awaiting_verification, 'Ready for an administrator', '◷'], ['Resolved tickets', summary.closed, 'Verified and closed', '✓']];
      html = `<div class="stats">${cards.map(([title, value, hint, icon]) => `<section class="stat"><div class="stat-top"><span>${title}</span><span class="stat-icon" aria-hidden="true">${icon}</span></div><strong>${value}</strong><small>${hint}</small></section>`).join('')}</div>`;
      html += panel('Recent maintenance tickets', 'Your latest reports and assignments', ticketTable(tickets.items), '<button class="text-button" data-go="tickets">View all tickets →</button>');
      html += `<div class="lower-grid">${panel('From reported to resolved', 'A clear path for every repair', '<div class="note-body"><ol class="steps"><li><div><strong>Report the issue</strong><br>Choose an asset and describe what needs attention.</div></li><li><div><strong>The right team takes over</strong><br>An administrator assigns a technician to the repair.</div></li><li><div><strong>Repair, verify, and close</strong><br>Completion proof and verification keep everyone informed.</div></li></ol></div>')}${panel('Your workspace', 'Only the records you have permission to see', `<div class="note-body"><p><strong>${escapeHTML(state.user.department)}</strong><br>${escapeHTML(label(state.user.role))} access</p><p>Counts include all your accessible tickets. Lists show the most recent items first.</p><button class="secondary" data-go="assets">Explore campus assets →</button></div>`)}</div>`;
    } else if (view === 'tickets') {
      const query = new URLSearchParams({ limit: '20' }); if (state.status) query.set('status', state.status); if (state.priority) query.set('priority', state.priority); if (state.cursor) query.set('cursor', state.cursor);
      const page = await api(`/tickets?${query}`); if (revision !== state.revision) return; state.next = page.next_cursor;
      html = panel('All maintenance tickets', 'Newest first · filtered to your access', filters() + ticketTable(page.items) + `<div class="pagination"><span>${page.items.length} tickets on this page</span><div><button class="secondary" id="first-page" ${!state.cursor ? 'disabled' : ''}>First page</button> <button class="secondary" id="next-page" ${!page.next_cursor ? 'disabled' : ''}>Next page →</button></div></div>`);
    } else if (view === 'assets') {
      const page = await api(`/assets?${new URLSearchParams({ q: state.assetSearch, offset: String(state.offset), limit: '30' })}`); if (revision !== state.revision) return; state.nextOffset = page.next_offset;
      const rows = page.items.length ? `<div class="table-scroll"><table><caption>Campus assets</caption><thead><tr><th>Asset</th><th>Department</th><th>Location</th><th>Status</th></tr></thead><tbody>${page.items.map(asset => `<tr><td><strong>${escapeHTML(asset.name)}</strong><span class="ticket-code">${escapeHTML(asset.asset_code)}</span></td><td>${escapeHTML(asset.department)}</td><td>${escapeHTML(asset.location || 'Not specified')}</td><td>${badge(asset.status)}</td></tr>`).join('')}</tbody></table></div>` : empty('No matching assets', 'Search by another asset name or code.');
      html = panel('Campus assets', 'Equipment and spaces in your department scope', `<form class="filters" id="directory-search"><input id="directory-query" aria-label="Search assets" placeholder="Search by asset name or code" maxlength="150" value="${escapeHTML(state.assetSearch)}"><button class="secondary">Search assets</button></form>${rows}<div class="pagination"><span>${page.items.length} assets on this page</span><div><button class="secondary" id="previous-assets" ${state.offset === 0 ? 'disabled' : ''}>← Previous</button> <button class="secondary" id="next-assets" ${page.next_offset === null ? 'disabled' : ''}>Next →</button></div></div>`);
    } else if (view === 'inventory') {
      const parts = await api('/parts?limit=100');
      html = panel('Spare parts stock', 'Up to 100 catalog items · stock across campus', parts.length ? `<div class="table-scroll"><table><caption>Spare parts inventory</caption><thead><tr><th>Part / SKU</th><th>Available</th><th>Reorder level</th><th>Unit cost</th><th>Stock status</th></tr></thead><tbody>${parts.map(part => `<tr><td><strong>${escapeHTML(part.name)}</strong><span class="ticket-code">${escapeHTML(part.sku)}</span></td><td>${part.stock_quantity}</td><td>${part.reorder_level}</td><td>${money(part.current_unit_cost)}</td><td>${badge(part.is_archived ? 'archived' : part.stock_quantity <= part.reorder_level ? 'high' : 'active').replace('>High<', '>Reorder needed<').replace('>Active<', '>In stock<')}</td></tr>`).join('')}</tbody></table></div>` : empty('No spare parts yet', 'An administrator can add stock through the inventory API.'));
    } else {
      const [costs, failures] = await Promise.all([api('/reports/costs'), api('/reports/failures')]);
      html = '<div class="lower-grid">' + panel('Maintenance cost by department', 'Completed work orders · labor and spare parts · up to 100 departments', costs.length ? costs.map(row => `<div class="cost-row"><span>${escapeHTML(row.code)}<small class="ticket-code">${row.completed_orders} completed work orders</small></span><strong>${money(row.total_cost)}</strong></div>`).join('') : empty('No costs recorded', 'Completed repairs will appear here.')) + panel('Frequently reported assets', 'Number of issue reports per asset · up to 100 results', failures.length ? failures.map(row => `<div class="cost-row"><span>${escapeHTML(row.asset_code)}</span><strong>${row.ticket_count} reports</strong></div>`).join('') : empty('No issues recorded', 'Asset reports will appear here as tickets are created.')) + '</div>';
    }
    if (revision === state.revision) $('#content').innerHTML = html;
  } catch (error) { if (revision === state.revision) { $('#content').innerHTML = empty('Could not load this view', 'Use the refresh button to try again.'); notify(error.message, true); } }
  finally { if (revision === state.revision) $('#content').removeAttribute('aria-busy'); }
}
function navigate(view) {
  if (!state.user) { $('#connect-dialog').showModal(); return; }
  if (view === 'reports' && !admin() || view === 'inventory' && state.user.role === 'student') return;
  state.cursor = null; state.offset = 0; notify(''); setHeading(view); render();
}
async function loadAssets() {
  const request = ++state.assetRequest;
  $('#find-assets').disabled = true;
  $('#report-form .form-error').textContent = '';
  try {
    const page = await api(`/assets?${new URLSearchParams({ q: $('#asset-search').value, limit: '100' })}`);
    if (request !== state.assetRequest || !$('#report-dialog').open) return;
    const reportable = page.items.filter(asset => asset.status !== 'retired');
    $('#report-asset').innerHTML = '<option value="">Choose an asset</option>' + reportable.map(asset => `<option value="${escapeHTML(asset.id)}">${escapeHTML(asset.asset_code)} · ${escapeHTML(asset.name)}</option>`).join('');
    $('#asset-hint').textContent = page.next_offset !== null ? 'More matches are available. Narrow your search to find the right asset.' : reportable.length ? 'Choose the asset that needs attention.' : 'No reportable assets match. Try a different name or contact your administrator.';
  } catch (error) { if (request === state.assetRequest && $('#report-dialog').open) $('#report-form .form-error').textContent = error.message; }
  finally { if (request === state.assetRequest) $('#find-assets').disabled = false; }
}
async function openTicket(id) {
  const detail = ++state.detail; const dialog = $('#ticket-dialog'); $('#detail-title').textContent = 'Ticket details'; $('#ticket-detail').innerHTML = '<p>Loading ticket…</p>'; if (!dialog.open) dialog.showModal();
  try {
    const [ticket, comments] = await Promise.all([api(`/tickets/${id}`), api(`/tickets/${id}/comments`)]);
    if (detail !== state.detail || !dialog.open) return;
    $('#detail-title').textContent = ticket.title;
    let actions = '';
    if (admin()) {
      const options = ticket.status === 'open' ? ['assign', 'reject'] : ticket.status === 'awaiting_verification' ? ['verify', 'rework'] : [];
      if (options.length) {
        const technicians = options.includes('assign') ? await api(`/dashboard/technicians?department_id=${encodeURIComponent(ticket.department_id)}`) : [];
        actions = `<form id="transition-form"><h3 class="section-title">Administrator actions</h3><label for="transition-action">Action</label><select id="transition-action">${options.map(action => `<option value="${action}">${label(action)}</option>`).join('')}</select>${technicians.length || options.includes('assign') ? `<label for="technician">Assign technician</label><select id="technician"><option value="">Choose a technician</option>${technicians.map(tech => `<option value="${tech.id}">${escapeHTML(tech.name)}</option>`).join('')}</select>` : ''}<label for="transition-reason">Reason (required except for assignment)</label><textarea id="transition-reason" maxlength="10000" rows="2"></textarea><p class="form-error" role="alert"></p><button class="secondary">Apply action</button></form>`;
      }
    }
    if (detail !== state.detail || !dialog.open) return;
    $('#ticket-detail').innerHTML = `<div class="detail-meta">${badge(ticket.status)} ${badge(ticket.priority, true)}<span class="ticket-code">#${escapeHTML(id.slice(0, 8).toUpperCase())}</span></div><div class="description">${escapeHTML(ticket.description)}</div><p>Reported by ${escapeHTML(ticket.reporter_name)} · ${escapeHTML(date(ticket.created_at))}<br>Assigned to ${escapeHTML(ticket.assignee_name || 'Unassigned')}</p>${actions}<h3 class="section-title">Discussion</h3><div>${comments.length ? comments.map(comment => `<div class="comment">${escapeHTML(comment.body)}<small>${escapeHTML(date(comment.created_at))}</small></div>`).join('') : '<p>No comments yet. Add an update below.</p>'}</div><p class="field-hint">Showing the first 20 comments, oldest first.</p><form id="comment-form"><label for="comment-body">Add a comment</label><textarea id="comment-body" required maxlength="10000" rows="3" placeholder="Share a useful update…"></textarea><p class="form-error" role="alert"></p><div class="dialog-actions"><button class="primary">Post comment</button></div></form>`;
    if (['closed', 'rejected'].includes(ticket.status)) $('#comment-form').innerHTML = '<p>This ticket is finalized. Its discussion is read-only.</p>';
    else $('#comment-form').onsubmit = event => submitForm(event, async () => { const body = $('#comment-body').value.trim(); if (!body) throw new Error('Enter a comment before posting.'); await post(`/tickets/${id}/comments`, { body }); if (detail === state.detail && dialog.open) await openTicket(id); });
    const transitionForm = $('#transition-form');
    if (transitionForm) transitionForm.onsubmit = event => submitForm(event, async () => {
      const action = $('#transition-action').value; const reason = $('#transition-reason').value.trim(); const technician = $('#technician')?.value;
      if (action === 'assign' && !technician) throw new Error('Choose a technician to assign.');
      if (action !== 'assign' && !reason) throw new Error('Enter a reason for this action.');
      await post(`/tickets/${id}/transitions`, { action, technician_id: action === 'assign' ? technician : null, reason: reason || null });
      notify('Ticket updated.'); if (detail === state.detail && dialog.open) await openTicket(id); render();
    });
  } catch (error) { if (detail === state.detail && dialog.open) $('#ticket-detail').innerHTML = `<p class="form-error" role="alert">${escapeHTML(error.message)}</p>`; }
}
async function submitForm(event, work) {
  event.preventDefault(); const form = event.currentTarget; const button = $('button[type="submit"], button:not([type])', form); const error = $('.form-error', form);
  if (button.disabled) return;
  const submission = Symbol('submission'); form.activeSubmission = submission;
  button.disabled = true; error.textContent = '';
  const isCurrent = () => form.activeSubmission === submission;
  try { await work(isCurrent); } catch (failure) { if (isCurrent()) error.textContent = failure.message; }
  finally { if (isCurrent()) { button.disabled = false; form.activeSubmission = null; } }
}
$('#connect-form').onsubmit = event => submitForm(event, async () => {
  const session = ++state.session;
  state.token = $('#token').value.trim(); if (!state.token) throw new Error('Enter your access token.');
  try {
    const user = await api('/me');
    if (session !== state.session || !$('#connect-dialog').open) return;
    state.user = user;
  } catch (error) { if (session === state.session) state.token = ''; throw error; }
  $('#token').value = ''; $('#connect-dialog').close(); $('#welcome').hidden = true; $('.topbar').classList.add('connected'); $('#connection-state').textContent = 'Connected';
  $('#user-name').textContent = state.user.name; $('#user-role').textContent = label(state.user.role); $('#avatar').textContent = state.user.name.slice(0, 1).toUpperCase();
  $('#department').textContent = state.user.department; $('#connection-button').textContent = 'Disconnect account'; $('#mobile-account').textContent = 'Disconnect';
  $$('[data-staff]').forEach(node => { node.hidden = state.user.role === 'student'; }); $$('[data-admin]').forEach(node => { node.hidden = !admin(); }); navigate('overview');
});
$('#report-form').onsubmit = event => submitForm(event, async isCurrent => {
  const title = $('#report-subject').value.trim(); const description = $('#report-description').value.trim();
  if (!title || !description) throw new Error('Enter a title and description with more than spaces.');
  await post('/tickets', { asset_id: $('#report-asset').value, title, description, priority: $('#report-priority').value });
  if (!isCurrent()) return;
  $('#report-dialog').close(); $('#report-form').reset(); state.status = ''; state.priority = ''; navigate('tickets'); notify('Issue reported. Your maintenance team can now review it.');
});
$('#new-ticket').onclick = () => { if (!state.user) { $('#connect-dialog').showModal(); return; } $('#report-form .form-error').textContent = ''; $('#report-dialog').showModal(); loadAssets(); };
$('#find-assets').onclick = loadAssets;
$('#asset-search').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); loadAssets(); } };
$('#welcome-connect').onclick = () => $('#connect-dialog').showModal();
$('#connection-button').onclick = () => state.user ? disconnect() : $('#connect-dialog').showModal();
$('#mobile-account').onclick = $('#connection-button').onclick;
$('#refresh').onclick = () => { if (state.user) { notify(''); render(); } else $('#connect-dialog').showModal(); };
$$('[data-view]').forEach(button => { button.onclick = () => navigate(button.dataset.view); });
$$('[data-close]').forEach(button => { button.onclick = () => button.closest('dialog').close(); });
// A closed dialog invalidates its pending UI work. Writes already accepted by
// the server may still finish, but cannot reopen or overwrite another dialog.
$$('dialog').forEach(dialog => dialog.addEventListener('close', () => {
  $$('form', dialog).forEach(form => {
    form.activeSubmission = null;
    const button = $('button[type="submit"], button:not([type])', form);
    if (button) button.disabled = false;
  });
  if (dialog === $('#ticket-dialog')) state.detail++;
  if (dialog === $('#report-dialog')) { state.assetRequest++; $('#find-assets').disabled = false; }
  if (dialog === $('#connect-dialog') && !state.user) { state.session++; state.token = ''; $('#token').value = ''; }
}));
$('#content').addEventListener('click', event => {
  const button = event.target.closest('button'); if (!button || button.disabled) return;
  if (button.dataset.ticket) openTicket(button.dataset.ticket);
  if (button.dataset.go) navigate(button.dataset.go);
  if (button.id === 'next-page') { state.cursor = state.next; render(); }
  if (button.id === 'first-page') { state.cursor = null; render(); }
  if (button.id === 'next-assets') { state.offset = state.nextOffset; render(); }
  if (button.id === 'previous-assets') { state.offset = Math.max(0, state.offset - 30); render(); }
});
$('#content').addEventListener('submit', event => {
  event.preventDefault();
  if (event.target.id === 'ticket-filters') { state.status = $('#status-filter').value; state.priority = $('#priority-filter').value; state.cursor = null; render(); }
  if (event.target.id === 'directory-search') { state.assetSearch = $('#directory-query').value.trim(); state.offset = 0; render(); }
});
