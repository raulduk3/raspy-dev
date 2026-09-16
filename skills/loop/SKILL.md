---
name: loop
description: Run one cycle of the daily development loop: sense open issues, pull requests, checks and health read-only; plan the sprint-ready issues who…
---

# loop

Run one cycle of the daily development loop: sense open issues, pull requests, checks and health read-only; plan the sprint-ready issues whose dependencies are merged and whose scopes are disjoint, up to the caps; post the plan comment on the pinned loop issue and wait for `steer: go` (hard gate); dispatch one worker per issue in its own worktree on its own branch; collect each pull request body and check status; post the cycle comment in the fixed format with one metrics line. State lives on GitHub only. Never merges, never pushes to a protected branch, never deploys.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
