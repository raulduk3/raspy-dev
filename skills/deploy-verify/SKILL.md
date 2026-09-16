---
name: deploy-verify
description: After a Testing or production deploy, read the deploy record, the running `/health` and `status` output, and the deploy log, and confirm tha…
---

# deploy-verify

After a Testing or production deploy, read the deploy record, the running `/health` and `status` output, and the deploy log, and confirm that the running version and build reference equal the deployed commit, that the store schema matches the release, that no active interaction was interrupted, and that the deploy-log row exists with version, commit, authorization and verification. Read-only; a mismatch is reported as a decision for the owner, never fixed in place.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
