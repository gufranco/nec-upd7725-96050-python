"""What this package raises, in one place so a caller can catch it by name."""

from __future__ import annotations


class UnknownModelError(Exception):
    """A model this package does not carry was asked for."""


class RunLimit(Exception):
    """A bounded run reached its limit without the condition it was waiting for.

    Raised rather than returned, because a caller that asked to run until
    something happens and got back a count has to remember to check it. A part
    that never reaches the condition is a program that does not terminate, and
    that is worth an exception.
    """


class ClockClosed(Exception):
    """The clock driving this part has been closed and cannot be advanced."""


class NotWholeWords(Exception):
    pass


class TooLarge(Exception):
    pass


class NeverReady(Exception):
    pass
