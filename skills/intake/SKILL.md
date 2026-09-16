---
name: intake
description: Turn a source (meeting notes, a call transcript, an email, the owner's notes, stored in the vault and never in a repository) into decision d…
---

# intake

Turn a source (meeting notes, a call transcript, an email, the owner's notes, stored in the vault and never in a repository) into decision drafts, each with context, options, consequences and a recommendation, filed as `decision` issues in the affected repository. An accepted decision that changes behavior becomes a spec pull request with its decision record; from the spec diff, cut implementable issues with `Scope:`, `Depends on:`, acceptance criteria citing spec sections and a milestone, labeled `needs-triage`. Every issue cites spec sections; every pull request cites its issue.

## Procedure

1. **Source.** One stakeholder record (meeting notes, a call transcript, an email, the owner's
   notes), quoted and dated. It stays in the owner's notes; it is never copied into a repository.
2. **Map** each takeaway to the specification and to open issues. A takeaway the specification
   already satisfies produces nothing. A takeaway it contradicts or leaves open produces one
   decision draft.
3. **Decision drafts**: context with the spec sections quoted, options, consequences, a
   recommendation, one question. Filed as `decision` issues in the affected repository through
   `loop/scripts/ghx`, on the owner's word.
4. **Spec change**: after the owner accepts a decision, one draft pull request edits the exact
   specification lines, sets the requirement status to `pending:#<decision issue>`, and adds the
   decision record under `docs/decisions/`.
5. **Cut issues** from the spec diff, each with `Scope:`, `Depends on:` (the spec pull request's
   issue), acceptance criteria citing spec sections, a milestone, and the label `needs-triage`.
6. **Traceability**: decision issue, then spec pull request citing it, then cut issues depending
   on it, then worker pull requests closing them. `gh` can walk the chain.
