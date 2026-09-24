# What comes across from OpenClaw, and what does not

The point of this migration is to lose weight. Most of what accumulated around
the OpenClaw agents was scaffolding for daily automations and personal-device
integrations that are not wanted again. What matters is the journal, the work
record, and the ability to bill from it.

## Verdicts

| Thing | What it did | Verdict |
| --- | --- | --- |
| `morty_log.py` | Knew where the daily log and daily note live | **Done.** It is `bin/journal`, which is now the only path authority. |
| `harvest.sh` | Hours and invoices against Harvest, credential in the Keychain | **Keep, by wrapping.** The one real integration worth carrying. |
| `daily_brief.py` | Morning brief | **Retired already**, with its job and discovery links removed. |
| `fitbit_connector.py` | Fitbit OAuth and collection through the gateway | **Drop.** A personal-device integration, not wanted. |
| `normalize_journal.rb` | One-shot journal normalization | **Drop.** Its work is done and the format is enforced in the tool now. |
| `ops.sh` | Talks to the ops agent on the VPS | **Drop from the personal role.** Host work is Neo's, and Neo reaches hosts directly. |
| `prune-sessions.sh` | Pruned OpenClaw transcripts | **Drop.** It only makes sense inside OpenClaw. |
| `idea-discovery` | Skill, but calls into `scripts/` | **Drop** unless the script it needs is rebuilt; it is not worth the dependency. |
| `job-interview-dossier` | Skill, prompt only | **Portable.** Load it as a role skill when wanted. |
| `vault-reorganization` | Skill, prompt only | **Portable**, though the vault tool now covers most of it. |
| `discord-bot-message-cleanup` | Skill over the Discord connector | **Drop.** No such connector here, and faking one would be worse than not having it. |
| `imessage-thread-reading` | Skill over the iMessage connector | **Drop**, same reason. |

## What replaced the parts worth keeping

The journal is the shared surface. Every role records work through one guided
verb that always writes today's note and cannot name a path, a date, or another
role's attribution. Each entry carries its project and the minutes it took, so
the personal role reconciles hours from structure rather than from prose, and
entries with no project are reported as unbillable rather than guessed at.

Memory replaced the habit of re-explaining context: each role carries its own
index in its launch context and reaches the rest, including everything its
original agent wrote, through a tool.

Obsidian is gone as a dependency. Its application config and vault scripts are
parked outside the vault under the platform state directory, with a manifest.
Every note was checksummed before and after and none changed. The vault is
plain Markdown in PARA folders, and Obsidian remains usable as a viewer if you
reinstall it, which will recreate its own config.

## What deliberately did not come across

No heartbeats, no schedules, no daily automations. Nothing runs unless a person
or a role asks for it. If a recurring job turns out to be wanted, it should be
built fresh against these tools rather than ported.
