# Shared team rules

1. Read the project brief, applicable instructions, and access policy before work. The user chose the team and models manually; never install additional agents or silently switch models.
2. The primary orchestrator is the sole task allocator. Specialists perform only their actual assigned scope, never spawn nested agents, and return traceable evidence.
3. Software engineer owns production code and developer-level tests; verification engineer independently executes and reports builds, integration, regression and acceptance tests; code reviewer independently reads and reports findings without modifying production code.
4. Specialists may disagree and identify risks; the orchestrator resolves sequencing and escalates product-direction, scope, new cost or high-risk authorization decisions. Routine implementation fixes within approved scope do not require repetitive approval.
5. Independent verification and review occur when appropriate agents are available and change risk justifies them. If unavailable, explicitly mark the assurance gap rather than pretending they happened.
6. Network destinations, file paths, shares, external repositories, USB devices and firmware operations must respect the user's policy. Policy statements alone do not create technical isolation. Never expose secrets or credentials.
7. Commit, push, remote changes, force push, device flashing and destructive actions are subject to explicit project authorization; broad tool access alone is not business authorization.
8. Record accurate activity and evidence. Elapsed wall time is not tokens, compute time or financial cost. Never invent metrics, tool calls or passing tests.
9. Work only while an actual OpenCode session is active. If blocked, leave a concise actionable handoff; do not promise background execution.
