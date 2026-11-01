# Adaptive workflow

1. Orchestrator reads PROJECT_BRIEF.md, TEAM_REGISTRY.md, AGENT_ACCESS_POLICY.json, AGENTS.md and active queue.
2. Verify which installed specialists are actually callable; log the inventory and significant gaps in .local-work/ACTIVE.md.
3. Plan the smallest next approved deliverable and its acceptance checks. Route task to the best available specialist based on role, not model name.
4. Software engineer (if present) implements; return affected files, results and limitations.
5. Verification engineer (if present) independently runs appropriate checks. On failure, send observations back to implementation owner. Code reviewer independently reviews significant changes. Small low-risk edits can skip formal review with a stated reason.
6. Orchestrator integrates the verified outcomes, tracks remaining gaps, and coordinates Git only within user-authorized operations.
7. Record next concrete action and continue through approved queue in the active session. Checkpoints are not stopping conditions. Do not invent runtime continuation after model/provider limits.

## Missing roles

If a specialist is absent, use only actual installed, permitted capabilities. Do not invent independent test evidence. Escalate only essential blockers. User controls role and model selection via agents-opencode.

## Handoff format

- Task and scope
- Owner
- Files changed or reviewed
- Test/review evidence with commands or references
- Open problems, confidence and limitations
- Recommended next action
