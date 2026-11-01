# Project workflow

## Kickoff (orchestrator + system-architect + technical-documenter)
1. Read `AGENTS.md`, `PROJECT_POLICY.md` and current repo status. If project classification/model/provider or Git remote access is unclear, resolve before work. Never assume that a privately classified project is cloud-shareable.
2. Architect inspects current architecture and identifies hard constraints, without automatically redesigning it. Documenter finds existing spec, decision and log locations.
3. Orchestrator writes a compact plan: task, minimum viable specialist set, files they may change, tests, branch strategy, resource expectations, approval boundaries.
4. Choose smallest required set from 20 optional specialists. Avoid 23-way consultation. Escalate only when evidence shows a gap.

## Images and screenshot analysis
1. When an image is relevant, orchestrator evaluates whether an image-capable specialist is needed; do not summon one for text-only tasks.
2. Verify that `image-analyst` has an image-capable configured model and the image is accessible inside the authorized project worktree or as an approved attachment.
3. Image analyst reports raw visual facts, legible values, observed defects, confidence and unanswered visual questions.
4. Pass only relevant details to DSP, RF, electronics, UX/UI or protocol specialists, who own technical conclusions. Do not repeatedly resend large images or analysis if a short reference suffices.

## Implementation and specialization
1. Delegate scoped tasks, preferably one writing subagent at a time in a shared checkout. If true parallel Git changes are needed, ask the user to approve explicit separate worktrees.
2. Specialists read project sources first, challenge unfounded claims, run short tests and report concise findings. Use the handoff template.
3. Programmer implements reusable code; domain specialists can produce small Python proofs of concept. Mathematicians document formal derivations; educator adapts them for the audience when needed.
4. Verification engineer uses a small first test, limited triage, then reports to orchestrator. Orchestrator authorizes only modest incremental expansion and asks user for substantial cost/time growth.
5. Code reviewer performs pragmatic independent checks when consequential. Architect handles structural review; documenter keeps meaningful changes current.

## Git integration
1. Orchestrator assigns a task branch `agent/<short-task>` (or existing project convention). Subagents do not independently merge into protected branches.
2. Make local commits after reviewing changes; do not include secrets. Keep status clean enough for reliable handoffs.
3. Orchestrator inspects diffs, reviews test evidence and coordinates integration; user approval required for major architecture changes and potentially destructive operations.
4. An authorized Git remote can be used through `.opencode/tools/git_sync.py` for fetch / ff-only pull / normal push of current branch. No remote configured = deny remote operations.
5. Documenter records meaningful outcomes and remaining work; orchestrator summarizes status, residual risks and any requests requiring user decisions.

## Compact specialist handoff example
```
Task: Implement timing recovery for an identified QPSK stream.
Verified: A small noise-free synthetic test converges with the proposed method.
Unknown: Behavior under high CFO and low SNR.
Tried: Short Python test at docs/research/qpsk_timing.py.
Files: docs/research/qpsk_timing.md; tests/test_timing.py.
Requested: software-engineer to implement module and one short deterministic test.
Budget/access: no full BER sweep; no internet; assigned repo only.
```
