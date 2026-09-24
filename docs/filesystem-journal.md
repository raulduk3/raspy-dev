# Filesystem journal

`bin/journal tasks` reads tasks directly from Markdown. It needs Python's standard library only and does not create an index or modify notes. Explicit daily-note commands below can write notes. Set `JOURNAL_ROOT` or provide `--root`; it never assumes the working directory is a journal.

```sh
bin/journal --root /path/to/journal tasks
bin/journal --root /path/to/journal tasks --tag work --due-on-or-before 2026-09-24
bin/journal --root /path/to/journal tasks --status all --path '2. projects/' --json
```

Default output gives absolute file paths and line numbers. JSON gives the root plus relative paths, line numbers, original task text, status, tags, priority, date fields, recurrence presence, and warnings. `--text` is a literal case-insensitive task-text filter. For full-note text search, use `rg -n --glob '*.md' 'search text' /path/to/journal`.

The default includes unchecked, in-progress, and unknown-status task lines. Unknown states remain visible for review. It excludes `0. morty`, `5. archive`, `6. templates`, and `7. data views`; `--include-history` includes them. Hidden paths and symlinks are always skipped. Historical tasks elsewhere in the corpus remain visible: this is a source view, not a claim that every unchecked task is still relevant. Fenced examples and frontmatter are skipped. Blockquoted checklists and arbitrary Markdown extensions are not parsed.

Dates retain existing emoji conventions. Invalid dates, repeated date fields, unknown statuses, and cancellation/status conflicts produce warnings. Date filters require a parsed due date. Recurrence text is preserved, but the tool does not calculate or create future occurrences. Existing query blocks are never executed.

This is the read-only first part of removing Obsidian dependencies. Task mutation, recurrence behavior, link navigation, corpus relocation, Things reconciliation, and Calendar integration still need their respective acceptance checks. Do not remove Obsidian or point writers at a second live journal based on this command alone.


## Daily notes and Morty logs

Adapted from the original Morty logging helper, these operations preserve the established date paths while removing hard-coded OpenClaw/Obsidian roots:

```sh
bin/journal --root /path/to/journal log-path 2026-09-24
bin/journal --root /path/to/journal log-ensure 2026-09-24
bin/journal --root /path/to/journal log-append 2026-09-24 --title 'Verified work' --body 'What actually happened.'
bin/journal --root /path/to/journal journal-ensure 2026-09-24
bin/journal --root /path/to/journal journal-line 2026-09-24 --line 'A short grounded summary.'
```

Omit the date to use today's date in America/Chicago. Omit `--body` to read from stdin. Morty logs remain under `0. morty/YYYY/MM/YYYY-MM-DD.md`; personal notes remain under `1. journal/YYYY/MM/DD-MM-YYYY.md`. New personal notes contain a title and `# Notes`, without application-specific task queries. Existing personal writing is retained; the tool does not generate prose or run automatically.

Appending the same titled section with the same body is a no-op. A different body under the same title is rejected rather than silently discarded. A journal line receives a link to that day's Morty log and is inserted under Notes, before any following top-level section. Repeating the line is a no-op. Legacy duplicate daily logs and symlink destinations are refused for deliberate reconciliation.

Writes are atomic and serialized among callers of this tool. A pre-replacement content check catches observed outside edits, but ordinary editors do not participate in the lock; this is not a general concurrent-edit synchronization protocol. Live migration must switch known writers together. The old helper and its live callers have not yet been replaced.

Validation covers real CLI writes, retry behavior, conflicts, placement within an existing note, legacy/symlink refusal, two concurrent log writers, and a write/retry on an isolated copy of an actual journal note. No live journal text was changed during validation.
