"""
MCP worker fork-safety helpers for macOS.

WHAT: Provides a platform-aware multiprocessing context factory and a
startup guard that ensures MCP worker processes on macOS are started via
the ``"spawn"`` method rather than ``"fork"``.

WHY: On macOS, forking from a multithreaded parent (Python event loop,
ThreadPoolExecutors, logging handlers) and calling CoreFoundation or
os_log APIs *before* ``exec()`` is forbidden — the kernel raises
``KERN_INVALID_ADDRESS`` / ``EXC_BAD_ACCESS``.  The specific crash path
is ``setproctitle`` (optional xdist / server-framework dep) →
``CFBundleGetFunctionPointerForName`` (CoreFoundation) in the child
process.  Using the ``"spawn"`` start method avoids the problem entirely
by creating a fresh Python interpreter rather than forking.

``OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`` is a band-aid that merely
suppresses the symptom; it is NOT the chosen fix here.

References
----------
LINK: none  (standalone utility; no governing spec yet)
"""

from __future__ import annotations

import multiprocessing
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.context import BaseContext


def get_mp_context() -> BaseContext:
    """Return the appropriate multiprocessing context for the current platform.

    WHAT: Returns a ``"spawn"`` context on Darwin (macOS) and the
    platform default elsewhere.

    WHY: Prevents EXC_BAD_ACCESS / SIGSEGV when child processes call
    CoreFoundation (via setproctitle or os_log) after a fork from a
    multithreaded parent.  Linux defaults to ``"fork"`` which is safe
    there, so we avoid imposing an unnecessary behavioural change.

    Returns
    -------
    multiprocessing.context.BaseContext
        A context object whose ``Process`` class uses the selected start
        method.

    Examples
    --------
    Replace::

        p = multiprocessing.Process(target=fn)

    With::

        ctx = get_mp_context()
        p = ctx.Process(target=fn)
    """
    if sys.platform == "darwin":
        return multiprocessing.get_context("spawn")
    return multiprocessing.get_context()


def ensure_spawn_on_darwin() -> None:
    """Guard: set the default multiprocessing start method to ``"spawn"`` on macOS.

    WHAT: Called once at process startup on Darwin so that any code using
    ``multiprocessing.Process(...)`` without an explicit context also gets
    the safe ``"spawn"`` method.

    WHY: Some transitive dependencies (uvicorn supervisors, huey worker
    launchers) create ``multiprocessing.Process`` objects without going
    through ``get_context("spawn")``.  Setting the default here provides
    defence-in-depth for those call sites.

    The call is silently skipped if the start method has already been set
    (``RuntimeError`` from ``set_start_method``) so this function is safe
    to call multiple times or from library code.
    """
    if sys.platform != "darwin":
        return
    try:
        multiprocessing.set_start_method("spawn", force=False)
    except RuntimeError:
        # Context already set — nothing to do.
        pass
