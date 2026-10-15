from __future__ import annotations


class UnknownModelError(Exception): ...


class RunLimit(Exception): ...


class ClockClosed(Exception): ...


class NotWholeWords(Exception):
    pass


class TooLarge(Exception):
    pass


class NeverReady(Exception):
    pass
