"""The three stores, each at its own width and its own length.

The part reads its instructions from one store twenty four bits at a time, its
constants from a second sixteen bits at a time, and it reads and writes a third
that is also sixteen. None of the three is byte addressed from the inside; only
the console sees bytes, and only of the third.

Nothing here starts clear unless it is asked to. Real silicon powers up holding
whatever it holds, and a model that starts at zero agrees with the part right up
until the first instruction that reads somewhere nothing wrote. A store can
therefore be given a source instead of a fill: a function of the address, called
only for words nothing has written yet. Filling four thousand words to read two of
them is waste, and a store that computes them on demand is the same store.
"""

PROGRAM_BITS = 24

WORD_BITS = 16

PROGRAM_BYTES_PER_WORD = 3

TABLE_BYTES_PER_WORD = 2

DEFAULT_FILL = 0


class TooLarge(Exception):
    pass


class NotWholeWords(Exception):
    pass


class Store:
    """A run of words of one width, addressed within its own length."""

    def __init__(self, words, bits, fill=DEFAULT_FILL, source=None):
        self.bits = bits
        self.mask = (1 << bits) - 1
        self.words = words
        self.source = source
        self._written = {}
        self._fill = None if source else (fill or 0) & self.mask

    def __len__(self):
        return self.words

    def __getitem__(self, at):
        at %= self.words
        held = self._written.get(at)
        if held is not None:
            return held
        return self._fill if self.source is None else self.source(at) & self.mask

    def __setitem__(self, at, value):
        self._written[at % self.words] = value & self.mask

    def changed(self):
        """Every address whose word is not what the store started with."""
        started = (
            (lambda at: self._fill)
            if self.source is None
            else (lambda at: self.source(at) & self.mask)
        )
        return {at: word for at, word in sorted(self._written.items()) if word != started(at)}


class Stores:
    """The program store, the constant table and the scratch the part shares."""

    def __init__(self, program_words, table_words, scratch_words, fill=DEFAULT_FILL, sources=None):
        sources = sources or {}
        self.program = Store(program_words, PROGRAM_BITS, fill, sources.get("program"))
        self.table = Store(table_words, WORD_BITS, fill, sources.get("table"))
        self.scratch = Store(scratch_words, WORD_BITS, fill, sources.get("scratch"))

    def read_byte(self, at):
        """One half of a scratch word, the low half from the even address."""
        word = self.scratch[at >> 1]
        return word >> 8 & 0xFF if at & 1 else word & 0xFF

    def write_byte(self, at, value):
        """The same halves, written without disturbing the other one."""
        where = at >> 1
        word = self.scratch[where]
        if at & 1:
            self.scratch[where] = (value & 0xFF) << 8 | word & 0xFF
        else:
            self.scratch[where] = word & 0xFF00 | value & 0xFF

    def load_program(self, image):
        _load(self.program, image, PROGRAM_BYTES_PER_WORD)

    def load_table(self, image):
        _load(self.table, image, TABLE_BYTES_PER_WORD)


def _load(store, image, per_word):
    if len(image) % per_word:
        raise NotWholeWords(f"{len(image)} bytes is not a whole number of {per_word} byte words")
    words = len(image) // per_word
    if words > len(store):
        raise TooLarge(f"{words} words will not fit in a store of {len(store)}")
    for at in range(words):
        word = 0
        for step in range(per_word):
            word = word << 8 | image[at * per_word + step]
        store[at] = word
