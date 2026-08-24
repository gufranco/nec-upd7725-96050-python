"""Driving a part one cycle at a time, the way a crystal drives one.

The family promises this class on every part, and a host driving a processor, a
coprocessor and this one should not have to learn three ways to advance them.

What it buys here is parity rather than resolution. On the two processors an
instruction spans several cycles, so a clock can stop half way through one and a
board can change what the next read answers. This part executes an instruction
in one external clock cycle, which the data sheet states outright, so a cycle
boundary and an instruction boundary are the same place and there is no inside
of an instruction to stop in. A caller wanting speed uses `step` or `run_for`; a
caller driving several parts against one wall uses this and gets the same shape
everywhere.

The mechanism is the one ares and bsnes use, and it is kept identical to the
sibling packages so the three behave the same: the part runs on a thread of its
own and blocks where the cycle is spent, rather than the instruction code
learning it can be interrupted. A cycle costs a pair of handoffs between two
threads, so this is far slower than `step`.

Only one thread runs at a time. The worker holds the part while the driver
waits, then the driver holds it while the worker waits, so nothing is shared
concurrently and no lock protects the processor itself.
"""

from __future__ import annotations

import threading
from types import TracebackType
from typing import Any

from .errors import ClockClosed


class Clock:
    """One part, advanced a cycle at a time rather than an instruction at a time.

    Built around a part, it takes over that part's `on_cycle` hook and gives it
    back when closed. A part being clocked must not also be stepped by hand: the
    worker is inside an instruction, and calling `step` from outside would run a
    second one on top of it.
    """

    def __init__(self, cpu: Any) -> None:
        self.cpu = cpu
        self.cycles = 0
        self.closed = False
        self._resume = threading.Semaphore(0)
        self._arrived = threading.Semaphore(0)
        self._failure: BaseException | None = None
        self._previous = cpu.on_cycle
        cpu.on_cycle = self._reached_a_cycle
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self) -> None:
        """Run the part forever, blocking inside every cycle it spends.

        This part has no halt, no wait and no stop: every encoding advances the
        counter, so `step` always completes and always costs one cycle. The 65xx
        package needs a second call here because a jammed part there completes no
        further instruction at all, and that difference is the hardware's rather
        than the design's, which is why this loop carries no branch it could
        never take.
        """
        self._resume.acquire()
        try:
            while not self.closed:
                self.cpu.step()
        except _Closed:
            pass
        except BaseException as failure:  # noqa: BLE001
            self._failure = failure
        self._arrived.release()

    def _reached_a_cycle(self) -> None:
        """Hand the part back to the driver, and wait to be given it again."""
        self._arrived.release()
        self._resume.acquire()
        if self.closed:
            raise _Closed

    def tick(self) -> int:
        """Advance the part by exactly one cycle, and report the total spent.

        Returns the running total rather than one, because one is the answer
        every time and a total is what a caller pacing against a wall needs.
        """
        if self.closed:
            raise ClockClosed("this clock has been closed")
        self._resume.release()
        self._arrived.acquire()
        if self._failure is not None:
            failure, self._failure = self._failure, None
            self.closed = True
            raise failure
        self.cycles += 1
        return self.cycles

    def run_for(self, cycles: int) -> int:
        """Advance exactly this many cycles, no more and no fewer.

        The difference from the part's own `run_for` is the whole point of this
        class. That one spends whole instructions and overshoots, because an
        instruction cannot be cut in half. This one stops between any two cycles,
        including the middle of an instruction, because that is where a board
        would.
        """
        for _ in range(cycles):
            self.tick()
        return self.cycles

    def close(self) -> None:
        """Let the worker go, and give the part its hook back."""
        if self.closed:
            return
        self.closed = True
        self._resume.release()
        self._arrived.acquire()
        self._worker.join(timeout=5.0)
        self.cpu.on_cycle = self._previous

    def __iter__(self) -> Clock:
        return self

    def __next__(self) -> int:
        if self.closed:
            raise StopIteration
        return self.tick()

    def __enter__(self) -> Clock:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()


class _Closed(BaseException):
    """Raised inside the worker to unwind it when the clock is closed.

    A BaseException rather than an Exception so that no `except Exception` in an
    instruction can swallow it and leave the thread running after the driver has
    gone.
    """
