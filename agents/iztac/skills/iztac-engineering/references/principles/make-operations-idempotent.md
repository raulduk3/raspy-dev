# make-operations-idempotent

Design retries to recover from partial execution.

Identify existing resources before creating successors, and verify their identity rather than relying on a PID or timestamp alone. Never replay an externally consequential action merely because its acknowledgement was lost.
