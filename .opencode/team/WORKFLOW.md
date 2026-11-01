# Delivery workflow

## Start or resume
1. Read applicable `AGENTS.md`, team/access rules and project policy. Inspect current Git state and preserve existing work. Use compact active memory if present; load only relevant specification/history sections unless project instructions explicitly require more.
2. Extract the user's authorized scope, priority order and observable acceptance criteria. For a finite request, stop at that scope; for an approved roadmap segment, keep a queue across increments. Missing nonblocking details become recorded questions, not a project-wide halt.
3. Select the next feasible item. Identify affected files, dependencies, checks and actual resource/permission limits. Choose installed specialists only when authorized and useful; the primary can act directly.

## Implement → verify → integrate → continue
1. Implement the smallest complete change in the project-selected language and architecture. Delegate concrete non-overlapping deliverables through the primary; do not rely on nested specialist calls.
2. Build/run the relevant checks. Diagnose failures, correct the implementation and rerun affected checks. Expand verification when failures, changed behavior or risk justify it; avoid repeated broad suites with no new reason. Report unperformed checks honestly.
3. Inspect specialist output and the combined diff, reconcile interfaces and validate integrated behavior. Update product documentation only for meaningful changes. Acceptance means the requested artifact exists, required checks pass (or an explicit blocker is recorded), and unresolved criteria are visible; a plan or handoff alone is not delivery.
4. Commit only if explicitly authorized, following project Git rules. Without commit permission, leave scoped verified work in the worktree and continue other authorized tasks.
5. Update the compact queue/state with evidence and the next action. If feasible authorized work remains, execute it now. A checkpoint, commit, version boundary or finished specialist assignment calls for a progress update, not a final answer.

## Recovery and questions
- On specialist/runtime failure inspect partial artifacts and error evidence. Preserve useful work, repair, reassign to approved available expertise, or complete it directly when competent. Avoid identical retry loops.
- Isolate blocked items and their dependants; continue independent tasks. Ask only for decisions required by the team authority table or project policy. A pending question does not suspend unrelated work.
- Respect actual provider/data/cost boundaries. Do not invent automatic provider fallback, remaining quota figures, or a promise of background work. Use parallel tasks only if supported and independently safe to integrate.

## Finish or forced interruption
- Before a final answer check whether the authorized queue still contains feasible work. Finish for completed scope, a user stop, exhausted explicit budget, an observed runtime limit, or all remaining tasks blocked after recovery/independent-work checks.
- Save a compact checkpoint in the repository-designated local work area: goal, completed/remaining criteria, changed files and Git state, exact test results, blockers and next executable action. Do not create a new user approval gate merely to review this checkpoint.
- State the real stopping condition, with observed errors/log references when available. Historical stop causes require session/log evidence; do not infer them from a convenient milestone.
- An ended OpenCode process/session is not automatically restarted by these rules. On resume inspect the worktree and checkpoint; do not assume an interrupted command or agent can resume automatically.

## Handoff
Use `HANDOFF_TEMPLATE.md` only when useful: goal and acceptance status, verified artifacts, unknowns/blockers, attempted recovery, exact file/test references, next action and real resource/permission limits. A specialist handoff returns control to the primary's continuing delivery loop.
