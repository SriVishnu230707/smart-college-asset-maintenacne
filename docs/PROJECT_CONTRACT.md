# Project contract: college assets and maintenance

Step 1 deliverable. These are the chosen business rules for the first version of this project. Later schema, SQLAlchemy, and API work must implement this contract. The examples in the [Step 1 lab](../labs/step-01/notes.md) specify expected outcomes; runtime enforcement has not been built yet.

An **invariant** is a rule that must still be true after a successful operation, a failed operation, or competing requests. For example, "show an insufficient-stock message" describes a response; "stock never becomes negative, and a failed repair consumes nothing" describes an invariant.

## 1. Identity and ownership

- Each user has one role: `student`, `technician`, `department_admin`, or `super_admin`. Users must be active to access the system. Every role except Super Admin belongs to exactly one department; a Super Admin may have no department.
- Every asset belongs to one department and one category. Asset statuses are `active`, `under_maintenance`, and `retired`. An existing non-retired asset can receive a new ticket, including while another issue is being repaired. Ticket status does not automatically change asset status.
- Each ticket permanently records its asset, reporter, and department at creation. The server takes the department from the asset and the reporter from the signed-in actor. A caller cannot supply another reporter or override the department.
- Assigned technicians must be active users with the technician role in the ticket's recorded department. An existing user ID alone does not make someone eligible.
- An asset transfer requires all its tickets to be terminal. After transfer, new tickets use the new department; existing tickets and their costs remain with the original department.
- User role/department changes or deactivation must not strand an assignment: reject them while that user is assigned to a nonterminal ticket or owns an active work order. Existing historical user references remain intact.
- UUIDs identify records. Unique department codes, category codes, asset codes, part SKUs, and normalized user emails identify their business identities independently. Historical asset codes and SKUs cannot be reused for a different record.

## 2. Role and resource permissions

Every request needs both an allowed action and access to the particular resource. Hiding a button is not enforcement. Deny actions that this table does not grant.

In this table, **own** means the ticket's reporter is the actor; **assigned** means the ticket is currently assigned to the actor; **department** means the actor's department matches the resource's department. Ticket scope always uses the ticket's recorded department, including for its comments, attachments, and work orders. All mutations must also satisfy the state rules below.

| Resource / action | Student | Technician | Department Admin | Super Admin |
|---|---|---|---|---|
| Read department identity | Own department | Own department | Own department | All |
| Create/change departments; manage category catalog | No | No | No | Yes |
| Read category catalog | Yes | Yes | Yes | Yes |
| Read assets | Department | Department | Department | All |
| Create/change/retire assets | No | No | Department | All |
| Transfer assets between departments | No | No | No | Yes, subject to section 1 |
| Manage users, roles, and activation | No | No | No | Yes, subject to section 1 |
| Report a ticket | Department asset, self as reporter | Department asset, self as reporter | Department asset, self as reporter | Any eligible asset, self as reporter |
| Read tickets and their comments/photos | Own | Assigned or own | Department | All |
| Edit original title/description | Own, while open | Own, while open | Own, while open | Own, while open |
| Triage priority; approve/assign/reject; verify repair | No | No | Department | All |
| Comment/add ticket photos | Own nonterminal ticket | Assigned or own nonterminal ticket | Department nonterminal ticket | Any nonterminal ticket |
| Read work orders, cost lines, and completion proof | No | Assigned | Department | All |
| Create/start/edit/complete work orders | No | Assigned, as work-order technician | No | No |
| Read central parts catalog, stock, and current prices | No | Yes | Yes | Yes |
| Manage suppliers, parts/prices, receipts, and stock corrections | No | No | No | Yes |
| Read suppliers and their contact details | No | No | No | Yes |
| Read inventory movement ledger | No | No | No | Yes |
| Read maintenance cost reports | No | No | Department | All |
| Read successful business audit history | No | No | Department events | All |
| Change/delete completed work, movements, or audit history | No | No | No | No |

Additional boundaries:

- Super Admin manages the workflow across departments, but repairs are performed by eligible assigned technicians. Administration never bypasses inventory, state, or immutability rules.
- A reporter retains read access to their own ticket history after a department change. Editing or commenting as a reporter additionally requires the actor to still belong to the ticket's department, except for a Super Admin.
- A technician who reported a ticket has reporter access; that does not grant repair or financial access unless assigned to it.
- An authorized ticket reader can read its comments and ticket photos. Work-order proof follows work-order read permissions. Neither relationship grants access to other tickets on the same asset.
- Password hashes are never returned. Assignment pickers expose only eligible technicians' IDs and display names, not unrestricted user records.
- Inventory is one college-wide pool in the first version. Department Admins can see availability; only Super Admin changes the pool. Department audit/report access excludes unrelated central inventory and user-administration events.

## 3. Ticket lifecycle

Ticket statuses are `open`, `assigned`, `in_progress`, `awaiting_verification`, `closed`, and `rejected`. `closed` and `rejected` are terminal.

| Operation | From | To | Actor and required conditions |
|---|---|---|---|
| Report issue | New | `open` | Authorized reporter; eligible asset; nonblank title and description; priority in `low`, `medium`, `high`, `critical` |
| Approve and assign | `open` | `assigned` | Department Admin in scope or Super Admin; eligible technician; approval and assignment are one operation |
| Reject report | `open` | `rejected` | Department Admin in scope or Super Admin; nonblank rejection reason |
| Start first repair | `assigned` | `in_progress` | Assigned technician starts the ticket's draft work order |
| Complete repair | `in_progress` | `awaiting_verification` | Assigned technician completes the active work order; all completion rules succeed |
| Accept repair | `awaiting_verification` | `closed` | Department Admin in scope or Super Admin; verification note; completed work exists; no active work order |
| Request further repair | `awaiting_verification` | `in_progress` | Department Admin in scope or Super Admin; nonblank rework reason; technician must create a new work order |

There is no separate `approved` state: approval and assignment happen together. No other state transition is allowed. A second ticket is required for a new issue after closure or rejection.

Priority may be triaged while `open` or `assigned`. Original report text can be edited only under the permission matrix while `open`; later clarification goes into comments. The asset, reporter, and recorded department never change.

Reassignment is allowed only while `assigned`, before any work order is started, and with no draft present. A draft can be explicitly discarded before reassignment. Starting, completing, verifying, and requesting rework must be serialized against each other so competing requests cannot leave contradictory states.

## 4. Work-order lifecycle

Work-order statuses are `draft`, `in_progress`, and `completed`.

- An assigned technician may create a draft while the ticket is `assigned` or `in_progress`. At most one work order per ticket may be active (`draft` or `in_progress`). A ticket may have multiple completed orders after rework.
- A work order permanently belongs to one ticket and one technician. Starting a draft changes it to `in_progress`; on the first repair it also starts the ticket. Starting a rework draft leaves the ticket `in_progress`.
- The owning assigned technician may edit draft/in-progress notes, labor cost, part lines, and proof while the ticket permits repair. There is at most one consolidated line per spare part per work order; quantities are positive whole numbers.
- A draft may be discarded, with an audit event, without changing stock. An in-progress work order must be completed; cancellation or reassignment of started repairs is outside the initial lifecycle.
- Completion requires nonnegative labor cost, a nonblank completion note, and at least one completion-proof attachment. A labor-only repair with no part lines and zero cost is valid.
- `completed` is terminal. Its technician, quantities, labor cost, part-price snapshots, completion note, proof metadata/storage references, and completion timestamp are immutable. Editing line/proof children is subject to the same rule as editing the parent.
- A request for rework never reopens an old completed order. A new work order records additional labor and parts; both repairs remain in historical costs.

## 5. Stock and the inventory ledger

For each part:

```text
stock_quantity >= 0
stock_quantity = SUM(all committed inventory quantity_delta values for the part)
```

An empty ledger means zero stock. `reorder_level` is a nonnegative whole number; alert when `stock_quantity <= reorder_level`.

| Movement kind | Quantity delta | Required context |
|---|---|---|
| `opening` | Positive | Optional initial stock when creating a part; at most one opening movement per part |
| `receipt` | Positive | Supplier reference and receiving actor |
| `consume` | Negative | Completed work order, part, and completing actor |
| `adjustment` | Nonzero, positive or negative | Super Admin actor and nonblank correction reason |

Zero opening stock creates no movement. Every balance change and its movement commit together. Nobody edits the stock balance directly or edits/deletes a committed movement. A correction appends an adjustment and must still leave stock nonnegative. It does not rewrite an old repair's quantities or costs.

Draft and in-progress part lines **do not reserve stock**. Two technicians may each draft a request for the last unit. Availability is decided again at completion. For each work-order/part pair there may be at most one `consume` movement, with delta equal to the negative frozen quantity used.

If any required part is short, the entire completion fails: no other part is consumed, no prices are frozen, and the work order and ticket remain in progress. After a receipt or an authorized edit to the unfinished order, a new completion attempt may succeed.

## 6. One atomic completion

The completion operation owns one transaction containing all of these effects:

1. Locate and protect the ticket and work order against competing workflow changes and child edits. Competing completion and editing operations must follow the same protocol.
2. Authorize the active actor against this ticket and work order, then resolve a previously completed operation as described in section 7.
3. Validate the current ticket/work-order states and the final part lines, costs, notes, and proof while that protection is held.
4. Establish exclusive access to all affected stock rows, using a consistent order across operations.
5. Check every required stock balance and capture each current unit cost.
6. Deduct stock and append consumption movements.
7. Freeze the work-order facts and mark it completed.
8. Move the ticket to `awaiting_verification` and append the completion audit event.
9. Commit all effects together.

Failure before commit leaves none of steps 5-8 committed. Success is reported only after commit. A lost success response does not undo the committed work; the caller retries the same work-order completion. If two different repairs compete for one unit, at most one can commit consumption; the other must observe insufficient stock after the winner commits, or proceed if the first transaction rolls back.

This is a required outcome, not a claim that a Python read followed by a write is safe. The concrete SQL/concurrency protocol is implemented and tested in later lessons.

## 7. Completion retries and returned result

The work-order ID identifies one completion operation. Completion is a command with no editable repair fields in its request; save draft changes through a separate edit operation before completing. This avoids using a retry to change the original quantities or cost.

- First successful completion returns the immutable completed result below.
- A retry by a currently authorized caller returns the same completed result. It does not consume stock, insert another success audit event, change timestamps, or alter the ticket state.
- Authorize before revealing a stored result. The owning technician must still have assigned access; an administrator with scoped work-order read access may retrieve an already completed result through the same retry operation, but cannot initiate completion of an unfinished order.
- Check for an existing completed result before applying the unfinished-work ticket-state checks. A retry still succeeds if the ticket was subsequently closed or returned for rework.
- Two simultaneous requests for the same work order produce one committed completion and the same result for both authorized callers. A caller waiting on a completion that rolls back may make the first successful completion instead.
- An unfinished work order with invalid state returns a state conflict. Insufficient stock returns an insufficient-stock conflict. Authorization failure reveals no result. These failures make no business changes. Exact HTTP status codes and transport shape belong to the API lesson.

The completed result contains:

| Field | Stable meaning |
|---|---|
| `work_order_id`, `ticket_id`, `technician_id` | Original identities |
| `status` | `completed` |
| `completed_at` | The original completion instant |
| `currency` | `INR` |
| `labor_cost` | Frozen labor cost |
| `parts` | Frozen lines ordered by part ID: `spare_part_id`, `quantity_used`, `unit_cost_at_use`, `line_total` |
| `parts_cost`, `total_cost` | Totals calculated only from these frozen values |

Current ticket status, remaining stock, current part prices, and mutable display names are not part of this stable result. Fetch their current values separately. Monetary values use exact two-decimal values; the eventual JSON representation uses decimal strings.

## 8. Historical cost and time

The initial system uses INR. Labor costs and unit prices are nonnegative exact values with two fractional digits. Reject values with excess fractional precision rather than silently rounding them. Quantities are integers.

```text
line_total = quantity_used * unit_cost_at_use
parts_cost = SUM(line_total), or 0.00 when no parts were used
work_order_total = labor_cost + parts_cost
ticket_total = SUM(all completed work_order_total values for that ticket)
department_total = SUM(completed work_order_total values attributed to ticket.department_id)
```

The unit price is the part's standard price at successful completion, not at draft creation. A draft may display an estimate; estimates do not enter historical reports. Completion must reject totals outside the chosen storage capacity; numeric precision is selected in Step 5.

Reports count completed work orders even while the ticket awaits verification or requires rework. Draft/in-progress estimates are excluded. Comments, attachments, and other joined children must not multiply repair totals.

Completed prices and labor costs never change when catalog prices change. Asset transfers never move existing repair costs to another department. Event timestamps represent instants; monthly reporting uses `Asia/Kolkata` and the work order's original `completed_at`.

## 9. History, deletion, audit, and attachments

| Record | Initial policy |
|---|---|
| Users | Deactivate; preserve IDs referenced by history; apply the assignment guard in section 1 |
| Departments and categories | Archive when no active resources need them; preserve referenced history |
| Assets | Retire; preserve tickets and historical identity; prevent new reports on retired assets |
| Suppliers and spare parts | Archive; block new receipts/consumption using archived records; a part must have zero stock and no active work-order lines before archival |
| Tickets and comments | Preserve; reject reports through the lifecycle rather than deleting them; comments are append-only |
| Draft work orders and draft children | Owning assigned technician may discard; record the discard in audit history |
| In-progress work orders | Preserve; editable only through the repair rules |
| Completed work orders and all their children | Preserve and make immutable |
| Inventory movements and business audit entries | Append-only; preserve actor and source references |

Archived departments cannot receive new users, assets, or tickets; archive only after their users/assets are inactive or retired and all tickets are terminal. Archived categories/suppliers cannot be selected for new assets/receipts; existing references remain readable. Referenced records are protected from hard deletion, including by direct database operations once the relevant constraints are installed.

Every successful mutation records actor ID, action, target type/ID, event instant, request identifier, and relevant change details. Ticket-scoped events also record the ticket's department for scoped audit reads. Completion records its frozen part and cost facts. Its success audit entry commits with the other completion effects. A rolled-back or denied operation leaves no success audit event; operational failure logs are separate. Completion retries do not duplicate business success events.

Attachment bytes live in file/object storage; the database stores ownership, storage key, filename, content type, size, and uploader. A completion-proof attachment must belong to that work order. The system must verify that the uploaded object exists before completion and protect completed proof from replacement/deletion. A failed completion may leave a previously uploaded file, but must not commit new completion metadata or inventory changes. Later storage integration must handle orphan uploads separately. Ticket readers cannot bypass attachment access through a public storage key.

## 10. Acceptance and later enforcement

The [Step 1 lab](../labs/step-01/notes.md) gives the required last-unit and duplicate-completion proofs plus additional acceptance cases. Use its scenario IDs when adding tests in later lessons.

| Invariant | Required rule | Later enforcement/verification steps |
|---|---|---|
| INV-01 | Action, role, active identity, and resource scope must all allow access | 34, 58, 59 |
| INV-02 | Business identifiers are unique; references and ticket department history remain valid | 3-7, 17, 23 |
| INV-03 | Only declared ticket/work-order transitions may occur | 35, 39, 44 |
| INV-04 | One active work order per ticket; one part line per work-order/part pair | 6, 24, 39, 44 |
| INV-05 | Stock never falls below zero; drafts reserve nothing | 6, 38, 43-44 |
| INV-06 | Stored stock equals the movement ledger, including opening stock | 38, 49, 59 |
| INV-07 | Completion commits every business effect together or none | 28, 40-46 |
| INV-08 | Repeated/simultaneous completion produces one effect and a stable result | 40, 44, 47 |
| INV-09 | Completed quantities, costs, proof, and completion time stay immutable | 5, 39, 44, 49-52 |
| INV-10 | Historical records and department attribution survive later changes | 7, 25, 49, 59 |
| INV-11 | Success audit history agrees with committed changes | 36, 40-41, 47 |
| INV-12 | Attachment access follows its parent and completion proof is preserved | 37, 39-40, 59 |

Read-only examples do not enforce a rule. Later database constraints must protect suitable row/reference rules; authorized use cases and transactions must enforce workflow and cross-record rules. Concurrency evidence must ultimately come from real PostgreSQL connections.
