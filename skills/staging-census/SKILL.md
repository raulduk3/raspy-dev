---
name: staging-census
description: "Deprecated: project-specific to one Testing host and its deploy log. Do not load unless that project names this skill."
---

# staging-census

**Deprecated 2026-09-24** (see `docs/skills-audit.md`). This contract was written for one
project's Testing host and was never exercised. It stays linked until the owner decides to remove
it or move it into that project's own repository.

Enumerate what is running on the Testing host read-only: containers, images and their version labels, rendered compose values, the release tree, the store schema version, active interactions, and the last deploy record. Compare with what `develop` says should be there and report differences. No mutation of any kind; a difference becomes an issue the owner triages.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
