---
name: intake
description: Turn a source (meeting notes, a call transcript, an email, the owner's notes, stored in the vault and never in a repository) into decision d…
---

# intake

Turn a source (meeting notes, a call transcript, an email, the owner's notes, stored in the vault and never in a repository) into decision drafts, each with context, options, consequences and a recommendation, filed as `decision` issues in the affected repository. An accepted decision that changes behavior becomes a spec pull request with its decision record; from the spec diff, cut implementable issues with `Scope:`, `Depends on:`, acceptance criteria citing spec sections and a milestone, labeled `needs-triage`. Every issue cites spec sections; every pull request cites its issue.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
