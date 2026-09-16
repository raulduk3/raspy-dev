---
name: staging-census
description: Enumerate what is running on the Testing host read-only: containers, images and their version labels, rendered compose values, the release t…
---

# staging-census

Enumerate what is running on the Testing host read-only: containers, images and their version labels, rendered compose values, the release tree, the store schema version, active interactions, and the last deploy record. Compare with what `develop` says should be there and report differences. No mutation of any kind; a difference becomes an issue the owner triages.

This is the contract. The procedure is filled in when the skill is first exercised, and it never widens beyond this paragraph without a decision.
