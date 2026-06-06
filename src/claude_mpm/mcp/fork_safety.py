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

import logging
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
    """Guard: guarantee the default multiprocessing start method is ``"spawn"`` on macOS.

    WHAT: Called once at process startup on Darwin.  Checks the current
    start method and forces it to ``"spawn"`` if it is not already set to
    that value, ensuring that any code using ``multiprocessing.Process(...)``
    without an explicit context gets the safe ``"spawn"`` method.

    WHY: Some transitive dependencies (uvicorn supervisors, huey worker
    launchers) create ``multiprocessing.Process`` objects without going
    through ``get_context("spawn")``.  Setting the default here provides
    defence-in-depth for those call sites.

    If another library has already set the start method to something other
    than ``"spawn"`` (e.g. ``"fork"``), this function overrides it with
    ``force=True`` and emits a warning — silently doing nothing would allow
    the SIGSEGV / EXC_BAD_ACCESS to recur.  ``force=True`` is safe here
    because this runs once at process startup before any child is spawned.

    If the forced call itself raises ``RuntimeError`` (belt-and-suspenders
    fallback for unexpected edge cases), the error is logged as a warning
    and the function returns without propagating into the serve entrypoint.
    """
    if sys.platform != "darwin":
        return

    _log = logging.getLogger(__name__)
    current = multiprocessing.get_start_method(allow_none=True)

    if current == "spawn":
        # Already correct — nothing to do.
        return

    if current is not None:
        _log.warning(
            "ensure_spawn_on_darwin: overriding existing start method %r to "
            "'spawn' for macOS fork-safety (issue #690)",
            current,
        )

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError as exc:
        # Belt-and-suspenders: log but never raise into the serve entrypoint.
        _log.warning(
            "ensure_spawn_on_darwin: forced set_start_method('spawn') failed: %s",
            exc,
        )
