"""A deterministic interleaving seam.

Real thread races are probabilistic, and a probe that reproduces a bug "usually"
is not a probe — it is a coin flip that occasionally lies. This module gives the
processor named checkpoints that do nothing in production and can be driven by a
test or probe to force one exact interleaving, every time.

The seam is deliberately trivial and deliberately in ``src``: it is the difference
between "we saw duplicate processing once on CI" and "duplicate processing is
reproducible on demand".
"""

from __future__ import annotations

import threading
from collections.abc import Callable

_coordinator: Callable[[str], None] | None = None
_lock = threading.Lock()


def checkpoint(name: str) -> None:
    """Yield control to the registered coordinator, if any.

    A no-op unless a probe or test has installed a coordinator.
    """
    coordinator = _coordinator
    if coordinator is not None:
        coordinator(name)


def set_coordinator(coordinator: Callable[[str], None] | None) -> None:
    """Install (or clear) the checkpoint coordinator."""
    global _coordinator
    with _lock:
        _coordinator = coordinator


class BarrierCoordinator:
    """Blocks every arriving thread at ``target`` until ``parties`` have arrived.

    Used to force the check-then-write window open deterministically: all workers
    are held between the "has this been done?" check and the write, so every one of
    them observes the pre-write state.
    """

    def __init__(self, target: str, parties: int, timeout: float = 10.0) -> None:
        self.target = target
        self._barrier = threading.Barrier(parties, timeout=timeout)

    def __call__(self, name: str) -> None:
        if name == self.target:
            try:
                self._barrier.wait()
            except threading.BrokenBarrierError:  # pragma: no cover - timeout path
                pass
