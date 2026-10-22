# Step 1: define and explain the invariants

Deliverable: [project contract](../../docs/PROJECT_CONTRACT.md). This lab is a worked requirements exercise. The scenarios below are acceptance specifications and reasoned walkthroughs, not executed database tests. SQL and ORM implementations arrive in later steps.

## What you are learning

A feature says what a user can do. An invariant says what must always remain true when that feature succeeds, fails, or competes with another action.

| Feature | Invariant |
|---|---|
| Technician completes a repair | Only its assigned technician may initiate completion |
| System deducts a spare part | Stock stays nonnegative and agrees with its movement ledger |
| Client retries after losing a response | One work order consumes its parts at most once |
| Admin changes a part's price | Completed repairs retain their original costs |

The contract makes these choices concrete through permissions, allowed states, and transaction outcomes.

## Proof A: two technicians request the last part

Scenario **S01**, covering INV-04 through INV-07 and INV-11:

Given:

- Technician A and Technician B each own a different in-progress work order on a different in-progress ticket in their permitted department.
- Each order requests one unit of the same part and has valid completion notes/proof.
- The part's stock is 1. Its ledger has an opening movement of +1. There are no consumption movements.

Both requests are valid drafts because drafts reserve nothing. Completion must decide against committed stock through a shared concurrency protocol.

| Event | A's order | B's order | Committed stock | Committed ledger |
|---|---|---|---|---|
| Before either completion | In progress | In progress | 1 | +1 opening |
| A obtains the right to consume and commits | Completed | In progress | 0 | +1 opening, -1 for A |
| B evaluates availability after A | Completed | Remains in progress; insufficient stock | 0 | Unchanged |

A's ticket becomes `awaiting_verification`; B's ticket remains `in_progress`. There is one successful completion audit event, attributed to A. B gets no frozen completion costs and no success event.

The labels may be reversed: the invariant does not choose a winning technician. If the first attempt rolls back, it consumes nothing and the second may succeed. At no committed point can both repairs consume that one unit.

Hand check:

```text
Final stock = opening 1 - successful consumption 1 = 0
Ledger sum = +1 + (-1) = 0
Committed successful completions = 1
```

A separate Python check followed by an unprotected write would not prove this outcome. The real two-connection experiment belongs to Steps 42-44 and 59.

## Proof B: completion submitted twice

Scenario **S02**, covering INV-07 through INV-09 and INV-11:

Given stock 3 and one in-progress work order needing 2 units at INR 250.00 each, with labor INR 100.00:

1. The first completion commits stock 1, one consumption movement of -2, frozen parts cost 500.00, total cost 600.00, and one completion audit event.
2. The response is lost, so the client retries completion for the same work-order ID.
3. After checking current authorization, the service finds the completed order and returns its original result. It makes no business changes.

| Observable value | After first commit | After authorized retry |
|---|---|---|
| Work order | Completed | Same completed order |
| Stock | 1 | 1 |
| Consumption movements for this order/part | One, delta -2 | Same one |
| Parts / labor / total | 500.00 / 100.00 / 600.00 | Same values |
| Completion instant | Original instant | Same instant |
| Completion success audit events | One | One |

The same rule holds for simultaneous duplicate requests and retries after the ticket is verified or returned for rework. An unauthorized caller cannot retrieve the result. A replay cannot change the quantity because completion carries no draft-edit payload.

## More acceptance scenarios

These cases make the rest of the contract reviewable before tables or endpoints exist. Failure cases preserve the prior business state and add no success audit event unless stated otherwise.

| ID | Given / when | Required outcome | Invariants |
|---|---|---|---|
| S03 | A Student attempts assignment, or a Department Admin accesses another department's ticket | Deny; no state change or sensitive result | INV-01, INV-11 |
| S04 | An admin assigns a Student, inactive technician, or technician from another department | Reject assignment; ticket remains open | INV-01, INV-02, INV-03 |
| S05 | An open ticket is closed directly, or a repair is rejected without a reason | Reject; only listed transitions and their conditions are allowed | INV-03 |
| S06 | Two active work orders are created for one ticket, or a second line is inserted for the same part | Reject the duplicate; retain at most one active order and one consolidated part line | INV-04 |
| S07 | Part X has stock 5, part Y has stock 0, and completion needs one of each | Neither part is consumed; stock stays 5 and 0; no completion costs/event/state change commits | INV-05, INV-06, INV-07 |
| S08 | An exception occurs after deduction but before completion/audit commits | Roll back balance, movements, frozen facts, work-order state, ticket state, and success audit together | INV-06, INV-07, INV-11 |
| S09 | A completed order used two parts at 250.00 plus labor 100.00; catalog price later becomes 300.00 | Historical total remains 600.00, not 700.00 | INV-09 |
| S10 | An admin requests rework after a 600.00 repair, then a new 50.00 labor-only order completes | Old order stays immutable; new order is separate; ticket total becomes 650.00 | INV-03, INV-04, INV-09 |
| S11 | An asset with a closed 600.00 ticket transfers from CSE to ECE | Old ticket and cost stay with CSE; future tickets use ECE; transfer during a nonterminal ticket is rejected | INV-02, INV-10 |
| S12 | A Super Admin tries to rewrite a completed part line, proof reference, or ledger movement, or delete a historical asset | Reject the change; retire/archive or append a permitted correction instead | INV-06, INV-09, INV-10, INV-12 |
| S13 | A stock correction would make stock negative, or uses a zero delta or no reason | Reject; balance and ledger stay unchanged | INV-05, INV-06 |
| S14 | An attachment belongs to another ticket/order, its object is missing, or the requester cannot read its parent | Reject attachment access/use; completion with invalid proof does not commit | INV-01, INV-07, INV-12 |
| S15 | A zero-part repair with labor 0.00 and valid notes/proof completes | Total 0.00; no stock movement; work order completes, ticket awaits verification, one success audit event | INV-03, INV-07, INV-09, INV-11 |
| S16 | A ticket has one 600.00 completed order, three comments, and two attachments | Its maintenance total is still 600.00 | INV-09 |
| S17 | Completion competes with a part-line edit, proof edit, or second completion | A single valid final order is frozen; an edit after completion is rejected; no unseen line/proof bypasses the completion decision | INV-03, INV-04, INV-07, INV-08, INV-09, INV-12 |
| S18 | A completed order's part is now out of stock, or its ticket was closed or returned for rework, and an authorized completion retry arrives | Return the same completed result; preserve current ticket state and stock; append no completion event | INV-01, INV-08, INV-09, INV-11 |
| S19 | A referenced user is deactivated or an asset/part is archived | Preserve historical references; reject deactivation that strands work and part archival while stock/active lines remain | INV-01, INV-02, INV-10 |

## Explain the design before advancing

Try answering these without looking at the worked proofs:

1. Why may two drafts each request the last part, and when is availability decided?
2. Which effects must disappear if completion fails after the first stock update?
3. Why is a retry for an already completed order checked before the unfinished ticket-state rules?
4. Why must authorization still run on a retry?
5. Why does requesting rework create another work order instead of reopening the first?
6. Why does the ticket keep its original department after an asset transfer?
7. Why does a database user foreign key not prove that an assignee is an eligible technician?
8. Which rule stops a Super Admin from editing a completed repair's cost?

Proof review: the required expected outcomes are derived above and the contract covers every acceptance scenario. Runtime proof remains for the database, workflow, and concurrency steps; your own ability to explain the rules is the learning gate.

Next: [Step 2 — understand the running database](../../docs/LEARNING_PATH.md). Start PostgreSQL and inspect its database, role, schema, and connection before creating application tables.
