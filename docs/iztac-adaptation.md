# Iztac engineering adaptation

Maintained source: `agents/iztac/skills/iztac-engineering/`. This belongs to Iztac's role resources, not the global skill collection shared by Morty and Neo. Its entry point gives ordinary-language routing and an inline index of all 23 adapted principles; each full rule is loaded only when relevant.

The source review covered every chapter of [the pstack guide](https://github.com/cursor/plugins/tree/12d587dfb20741cafc376c42c696c5f6e2a64487/pstack/docs/guide) at commit `12d587dfb20741cafc376c42c696c5f6e2a64487`, plus the 23 principle files. The adaptation uses original wording tailored to this ecosystem.

| Chapter | Application here |
| --- | --- |
| 1 | Use local platform tools and verified provider bindings; don't copy Cursor configuration |
| 2 | Route ordinary-language goals; preserve the selected workflow on continuation |
| 3 | Explain mechanisms and rationale from actual evidence; learning is a primary outcome |
| 4 | Compare alternatives when a consequential decision needs them; independent review does not grant release authority |
| 5 | Reproduce defects and verify behavior; preserve useful rationale while removing dead scaffolding |
| 6 | Inspect the actual candidate and separate checks, review, publication and deployed acceptance |
| 7 | Bound long work and retain one coordination owner; no imported timer or auto-merge system |
| 8 | Read the 23-principle index at multi-step task start; load applicable full rules progressively |
| 9 | Improve the skill from observed behavior, with reproducible checks rather than accumulating instructions |
| 10 | Keep user interaction simple; Iztac handles workflow mechanics without requiring command memorization |

Iztac requires an explicit project or project-formation directory. Conversations keep their own stable storage and link native sessions. OpenRig remains general-purpose and owns its supported coordination surface; dev-platform provides engineering conventions and tools. Active loop ownership is retained until explicitly transferred. Morty can read engineering evidence for journal or billing context but is not an engineering gate.

Validation: `quick_validate.py` accepts the skill. Run `node integrations/pi/check-role-skills.mjs` to exercise the pinned real Pi resource loader: Iztac receives exactly this skill, Morty/Neo receive none, unrelated repository context and skill discovery are suppressed, and all 24 reference links exist. These are loader checks, not evidence of authenticated agent reasoning or a complete production launcher. Role-scoped launch and live behavioral acceptance remain required.
