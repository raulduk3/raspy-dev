---
name: deploy-verify
description: "Deprecated: project-specific to one Testing host and its deploy log. Do not load unless that project names this skill."
---

# deploy-verify

**Deprecated 2026-09-24** (see `docs/skills-audit.md`). This contract was written for one
project's Testing host and was never exercised. It stays linked until the owner decides to remove
it or move it into that project's own repository.

After a Testing or production deploy, read the deploy record, the running `/health` and `status` output, and the deploy log, and confirm that the running version and build reference equal the deployed commit, that the store schema matches the release, that no active interaction was interrupted, and that the deploy-log row exists with version, commit, authorization and verification. Read-only; a mismatch is reported as a decision for the owner, never fixed in place.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
