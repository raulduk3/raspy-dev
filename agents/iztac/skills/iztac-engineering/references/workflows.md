# Task workflows

Read only the section selected by the session entry point. These are adaptations of pstack's playbooks, not installed upstream slash commands.

## Frame
For a raw source, use distill to compare candidates with current specification and existing work. Keep private source material outside professional repositories. Promote accepted scope through intake, separating owner decisions from implementation facts. Technical Design Description (TDD.md) is not test-driven development. A simple already-specified fix can proceed directly to its bounded issue. Finish with intent, dependencies, acceptance evidence and implementation-ready scope; do not manufacture issues for every thought.

## Understand
Trace the concrete entry point, data path, state ownership and failure path. For rationale, consult relevant history and design/issue records; preserve the difference between recorded reasons and inferred intent. Use only available sources needed to resolve the question, not a compulsory seven-source fan-out. Runtime forensics observes the symptom with scoped instrumentation; trace forensics preserves and analyzes the captured artifact. Report what the evidence establishes, competing explanations and the smallest next experiment. Diagnosis does not authorize a fix.

## Learn
Start with what the thing is, follow its real mechanism through a small code/example path, and explain why that design was chosen with the evidence's original uncertainty. Use the current diff, debugger or experiment when it makes the concept concrete. Add diagrams only when they help. Match depth to the user's question; do not impose a quiz or lecture. Learning need not mutate code or dispatch a second agent.

## Build
Name the domain shape, caller contract and owner of mutable state before introducing an abstraction. Investigate unfamiliar code before designing the change. For a defect, reproduce the observed failure on its real surface. If a cheap clear regression target exists or the user requested test-first, run the failing check before fixing and then demonstrate it passes. Otherwise use the closest honest reproducible evidence; do not invent a mock-heavy harness to satisfy ceremony.

For a feature, choose the smallest coherent implementation and its success/failure evidence. For a refactor, pin observable behavior before changing structure. For a visual change, compare against the target on the same relevant dimensions and states. A prototype answers one empirical design question and is not production-ready by assertion. Compare alternatives only when they resolve a consequential unknown; no mandatory multi-model contest.

Use the existing loop or a bounded isolated coding worker according to surface rules. One writer per worktree. Bind a focused offshoot to its parent task and commit, explicitly select sibling commits, and submit evidence for combined verification. Do not automatically cherry-pick live unfinished work. Finish with the actual diff, check output and candidate reference.

## Improve
Capture a representative workload and measured baseline. State the metric, success threshold, resource bound and regressions to protect. Test one hypothesis, compare equivalent runs, and retain changes only for an observed improvement without unacceptable regressions. A hillclimb is an explicitly bounded series of these steps, not perpetual autonomous tuning. Preserve the workload and measurement script so another session can reproduce it.

## Review
Inspect the candidate diff and its requirements. Independently reproduce the consequential behavior and assess scope, failure paths and evidence gaps. Use additional reviewers for justified independent work, not a compulsory panel. Confirm the current head SHA before applying prior CI/review results. An eval of a skill/prompt needs representative tasks, fixed artifacts and an observable decision/result, with uncertainty for small samples.

A PR-status request is one status check unless continued monitoring was requested. Distinguish conflict-free, checks-passing, reviewed, authorized, merged, deployed and verified. Automated comments are findings to verify; dismiss false positives with evidence without unnecessary churn. Follow repository publication rules. A green stack does not grant authority to merge it.

## Program
Resolve the existing coordination owner first; retain an active loop until an explicit handover. Break the outcome into dependency-ordered, independently checkable tasks with bounded worker concurrency, turns/time and available account capacity. Delegate only through supported native workers under the platform's rules. Workers receive goal, scope, relevant file pointers, checks, bounds and expected result. Review their changes rather than forwarding summaries as proof.

Keep decision/evidence pointers in the existing task artifacts and progress card. Continue independent authorized work around blockers; stop the affected lane for missing authority, unusable credentials or a failed precondition. Keep a concrete done predicate. Do not install pstack's separate orch ledger, Cursor /loop timers, cloud dispatcher or Benny schedules. The conversation checkpoint reports completed evidence, incomplete work, running processes and the next action.

## Continue/Pause
Read the existing handoff and inspect current Git/native-session state before continuing. Preserve explicit account/runtime ownership and owner titles. Check discrepancies instead of blindly trusting or redoing all previous work. Pause prevents new dispatch; inspect and report active workers separately. Save unfinished edits and specific resume instructions without sweeping unrelated work into a commit. A new harness continues the task through its checkpoint; it is not the same native conversation.

## Maintain
For durable reusable procedure changes, edit the maintained skill source, use available skill-authoring guidance, and follow the applicable publication policy. Verify the behavior on representative inputs; repair evidenced problems, not speculative universal rules. For worktree/session cleanup, census references, dirtiness, live ownership and recoverability first. Keep uncertain or active history; do not equate untracked with disposable or use an assumed origin/main base.
