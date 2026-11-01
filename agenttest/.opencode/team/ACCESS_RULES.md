# Access rules

`AGENT_ACCESS_POLICY.json` is the explicit project policy selected by the user.
Network allowlists/denylists, hardware selectors, Git remote/branch restrictions and share paths that are not enforceable by the supported OpenCode tool gates remain **advisory**. Do not claim they provide isolation.
For strong guarantees, configure OS sandboxing, restricted user/VM/container, filesystem ACLs, restricted SSH keys, Git server protection and host firewall externally. In unattended mode, ASK may be auto-approved: use DENY for operations that must never occur.
