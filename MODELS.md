# Model routing

Which class of model does which class of work. Every fleet or workflow run carries a token ceiling and an agent-count ceiling and stops on a quota error. Cost is a tie-breaker, never the first criterion.

| Tier | Work | Models |
| --- | --- | --- |
| Judgment | Specification, decisions, review, the root loop | Fable or Opus, low to medium effort |
| Implementation | A bounded issue with a deterministic check behind it | Sonnet, Codex default |
| Mechanical | Triage, formatting, summaries | Haiku, local |

Rules:

1. A cheaper model only where a check catches its mistakes. If no check would catch a wrong answer, the work is judgment work.
2. Escalate one tier on failure without asking. A second failure at the judgment tier stops and reports.
3. Every dispatched run states its ceiling: tokens per worker, agents per cycle, wall-clock per cycle. A run with no ceiling is not dispatched.
4. On a quota error, stop the lane, name the account, and do not retry on another account until the routing table below says so.

Routing table (fallback order on a quota error; edit here, never improvise):

| Lane | First | Then | Then |
| --- | --- | --- | --- |
| Judgment | primary account, Fable | primary account, Opus | stop and report |
| Implementation | primary account, Sonnet | Codex default | stop and report |
| Mechanical | Haiku | local model | stop and report |

Which account is primary for which surface is a separate decision (spec B2.1, D-13) and is recorded here once made.
