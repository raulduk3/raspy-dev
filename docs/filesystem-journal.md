# Filesystem journal

`bin/journal` reads tasks directly from Markdown. It needs Python's standard library only and does not create an index or modify notes. Set `JOURNAL_ROOT` or provide `--root`; it never assumes the working directory is a journal.

```sh
bin/journal --root /path/to/journal tasks
bin/journal --root /path/to/journal tasks --tag work --due-on-or-before 2026-09-24
bin/journal --root /path/to/journal tasks --status all --path '2. projects/' --json
```

Default output gives absolute file paths and line numbers. JSON gives the root plus relative paths, line numbers, original task text, status, tags, priority, date fields, recurrence presence, and warnings. `--text` is a literal case-insensitive task-text filter. For full-note text search, use `rg -n --glob '*.md' 'search text' /path/to/journal`.

The default includes unchecked, in-progress, and unknown-status task lines. Unknown states remain visible for review. It excludes `0. morty`, `5. archive`, `6. templates`, and `7. data views`; `--include-history` includes them. Hidden paths and symlinks are always skipped. Historical tasks elsewhere in the corpus remain visible: this is a source view, not a claim that every unchecked task is still relevant. Fenced examples and frontmatter are skipped. Blockquoted checklists and arbitrary Markdown extensions are not parsed.

Dates retain existing emoji conventions. Invalid dates, repeated date fields, unknown statuses, and cancellation/status conflicts produce warnings. Date filters require a parsed due date. Recurrence text is preserved, but the tool does not calculate or create future occurrences. Existing query blocks are never executed.

This is the read-only first part of removing Obsidian dependencies. Task mutation, recurrence behavior, journal writes, link navigation, corpus relocation, Things reconciliation, and Calendar integration still need their respective acceptance checks. Do not remove Obsidian or point writers at a second live journal based on this command alone.
