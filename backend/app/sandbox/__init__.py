"""Sandbox - owner: Dev 4. See SHARED_CONTRACTS §2, §8.

The public surface Dev 2's orchestrator calls. Everything that executes repository
code goes through `runner`; everything that writes candidate files goes through
`workspaces`.

The placeholder that used to stand in for `runner_status` is gone; it is now a
real Docker probe. SHARED_CONTRACTS §0.2 requires every temporary stand-in to be
deleted before the Sat 17:00 dry run, and CI greps for them on every push.
"""

from app.sandbox.runner import (
    is_available,
    run_behaviour_cases,
    run_compileall,
    run_pytest,
    runner_status,
)
from app.sandbox.workspaces import (
    BASELINE_REVISION,
    accept_workspace,
    apply_patch,
    create_workspace,
    diff,
    revision_path,
    workspace_path,
)

__all__ = [
    "BASELINE_REVISION",
    "accept_workspace",
    "apply_patch",
    "create_workspace",
    "diff",
    "is_available",
    "revision_path",
    "run_behaviour_cases",
    "run_compileall",
    "run_pytest",
    "runner_status",
    "workspace_path",
]
