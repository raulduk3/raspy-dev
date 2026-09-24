# separate-before-serializing-shared-state

Give independent workers independent write locations.

Use one writer per worktree. Serialize only genuinely shared authority such as claiming one task or reserving bounded account capacity; model instructions alone cannot enforce this.
