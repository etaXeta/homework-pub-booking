# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

In my Ex7 run (session `sess_465e11330e74`), the loop-half planner successfully identified the need to hand off to the structured half for final confirmation. In the first round, the planner called `venue_search` and found "Haymarket Tap" (venue_id: `haymarket_tap`) for a party of 12. Immediately following this, it invoked the `handoff_to_structured` tool. The reasoning provided by the model in the tool call arguments was: "loop half identified a candidate venue; passing to structured half for confirmation under policy rules."

This decision was driven by the explicit requirement in the task description to verify the booking against strict rules (party size and deposit caps). The planner recognized that while it could research and find a venue, the final "commit" operation required the specialized logic of the structured half. The signal was the deterministic nature of the "confirmation" step compared to the open-ended "research" step. The handoff payload included the action `confirm_booking` and the venue details, signaling a transition from information gathering to formal rule validation. This demonstrates the "advisory" role of the loop-half planner in a hybrid architecture; it doesn't just halt, it proactively routes the task to the component best suited for the next subgoal.

### Citation

- `sessions/ex7-handoff-bridge/sess_465e11330e74/logs/tickets/tk_279a1a0c/raw_output.json` (lines 18-34)
- `sessions/ex7-handoff-bridge/sess_465e11330e74/logs/trace.jsonl` (line 5)

---

## Q2 — Dataflow integrity catch

### Your answer

While my successful runs in session `sess_04308300d10b` passed the integrity check, the implementation of `verify_dataflow` in `integrity.py` is designed to catch fabrications that a human reviewer would easily miss. A plausible failure scenario involves the `calculate_cost` tool and the deposit calculation. If `calculate_cost` returns a `total_gbp` of 556 and a `deposit_required_gbp` of 111 (as seen in my tool logs), a human reviewer might accept a flyer that slightly "rounds" these numbers for aesthetic reasons—for example, claiming "Total: £550, Deposit: £110." To a human, this looks like a minor, perhaps intentional, simplification.

However, the `verify_dataflow` check would catch this immediately. The `extract_money_facts` function would identify "£550" and "£110" in the flyer. The `fact_appears_in_log` helper would then search for the scalar values `550` and `110` in the `_TOOL_CALL_LOG`. Since the tool actually returned `556` and `111`, the check would fail with `ok=False` and list the simplified figures as `unverified_facts`. This is a specific instance where a human's "common sense" or tolerance for minor discrepancies allows a hallucination to slip through, whereas the agent's strict scalar-matching discipline ensures that every digit in the final output is backed by an auditable tool response. This prevents the "drifting" of facts between tool execution and final report generation.

### Citation

- `starter/edinburgh_research/integrity.py` (lines 118-164)
- `sessions/ex5-edinburgh-research/sess_04308300d10b/logs/trace.jsonl` (lines 5-7)

---

## Q3 — Removing one framework primitive

### Your answer

If I were shipping this to a real business, the first production failure I'd expect is a partial or corrupted state write during high-concurrency or system-crash events, and the sovereign-agent primitive that would surface (and ideally prevent) it is **IPC atomic rename**. In a real-world pub booking environment, multiple agents or external processes might be interacting with the same session directory. Without atomic renames, an agent might crash halfway through writing a `manifest.json` for a new ticket, leaving a malformed or empty file.

When a subsequent process (like the orchestrator or a monitoring dashboard) attempts to read the session state, it would encounter a broken file. The atomic rename primitive ensures that the new state only appears in the filesystem once the write is fully completed and flushed to disk. If this primitive were missing, we would see "ghost" tickets or sessions that appear to be in a certain state but are actually missing their content. The failure mode would be a "File Not Found" or "JSON Decode Error" during a critical state transition. By surfacing this failure at the filesystem level—where the file either exists in its entirety or does not exist at all—the framework avoids the far more difficult-to-debug scenario of "partial truth." This allows for clean retries and state recovery, which are essential for a reliable booking system.

### Citation

- `ASSIGNMENT.md` (lines 154-158) - referencing atomic renames and manifest discipline.
- `starter/handoff_bridge/bridge.py` - where session state transitions are managed.
