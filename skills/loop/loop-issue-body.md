Pinned. One comment per daily cycle, in the fixed format below. Nothing else lives here.

Cycle: sense (read-only), plan, gate, dispatch, collect, report. Once per weekday morning,
America/Chicago. Only `sprint-ready` issues whose body carries `Scope:` and `Depends on:` lines
are selected; dependencies must be closed; scopes must not overlap within a cycle. Workers get
one issue, one worktree, one branch, one draft pull request. The engineering owner reviews
locally, marks ready, and merges in dependency order.

Gate: hard. A plan is dispatched only after a `steer: go` comment dated the same day.

Steering, as comments on this issue:

```
steer: go | pause | skip <n> | only <n> | budget <tokens> | note <text>
```

Cycle comment format:

```
CYCLE YYYY-MM-DD
plan: <issues and chains>
done: <issue pr#N checks>
waiting: <issue reason>
blocked: <issue decision #N>
decisions: <new decision issues>
lessons: <count appended>
metrics: planned N dispatched N prs N green N decisions N tokens N wall Nm
```

Metrics are one line per cycle, queryable with `gh issue view --comments`.
