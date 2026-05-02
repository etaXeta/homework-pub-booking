# Ex5 — Edinburgh research loop scenario

## Your answer

The planner produced five subgoals (sg_1 to sg_5) to research an Edinburgh
pub, check the weather, calculate costs, and produce a flyer. All subgoals
were assigned to the loop half.

Execution in `sess_04f5334d7d7b` showed significant live-model drift. The
executor initially struggled with the required tool sequence, attempting
to hand off to structured mode (which was disabled) and trying to complete
the task before all required tools had successfully run. It eventually
drifted into redundant searches for "city center" and "Old Town" before
triggering the deterministic recovery mechanism in the scenario runner.

The recovery mechanism executed the canonical tool chain (`venue_search` ->
`get_weather` -> `calculate_cost` -> `generate_flyer`) to produce the final
`workspace/flyer.md` for the Haymarket Tap. The dataflow integrity check
verified four key facts in the flyer (Venue Name, Weather, Total Cost, and
Deposit) against the tool call logs, ensuring no hallucinations were
present in the final artifact.

## Citations

- `sessions/ex5-edinburgh-research/sess_04f5334d7d7b/logs/trace.jsonl` — tool call sequence and drift recovery
- `sessions/ex5-edinburgh-research/sess_04f5334d7d7b/workspace/flyer.md` — the produced flyer
