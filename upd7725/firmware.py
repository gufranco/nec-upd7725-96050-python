"""A firmware image its owner supplies, identified before it is run.

The processor is complete without any of this. Every instruction it has is settled
by generating instruction words, and none of that needs a program anybody wrote.
An image is only needed to run one particular cartridge's part, and that image
belongs to whoever wrote it, so it is never carried here and never will be.

What is carried is the manifest: what each image is, how long it is, and the digest
that decides whether the copy on your disk is the one it claims to be. A digest
identifies a file and reconstructs nothing, which is the difference between saying
what something is and handing it over.

A file that does not match is diagnosed rather than merely refused. Being told that
a digest failed leaves you no wiser; being told the file is the right length with
different content, or the other revision, or an archive rather than the thing
inside it, tells you what to do next.
"""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = ROOT / "artifacts.manifest.json"

DIRECTORY_VARIABLE = "UPD7725_FIRMWARE_DIR"

DEFAULT_DIRECTORY = ROOT / "firmware"

ALONGSIDE = ROOT.parent / "firmware"
"""Where a project that carries this package as a submodule keeps its own images.

A submodule that only looks inside itself makes every project that uses it keep a
second copy of files it may not distribute. So the directory beside this one is
searched first: a project checks this package out under its own tree, puts its
images in its own firmware directory, and neither side has to be told about the
other."""

PROGRAM_BYTES_PER_WORD = 3

TABLE_BYTES_PER_WORD = 2

READABLE_SUFFIXES = (".bin", ".rom")


class Unrecognised(Exception):
    pass


class WrongShape(Exception):
    pass


class Identity:
    """What an image turned out to be."""

    def __init__(self, part, processor, revision, program_words, data_words):
        self.part = part
        self.processor = processor
        self.revision = revision
        self.program_words = program_words
        self.data_words = data_words

    def __repr__(self):
        return f"<Identity {self.part} {self.revision} on {self.processor}>"


def manifest(path=None):
    with Path(path or MANIFEST).open() as handle:
        return json.load(handle)


def directory(environment=None):
    """The first place images are looked for."""
    return directories(environment)[0]


def directories(environment=None):
    """Every place images are looked for, in the order they are looked at.

    Whatever was named comes first, then the project this package sits inside if
    it is a submodule of one, then this package itself. More than one can be
    named at once, separated the way the operating system separates a path.
    """
    named = (environment if environment is not None else os.environ).get(DIRECTORY_VARIABLE, "")
    wanted = [Path(where) for where in named.split(os.pathsep) if where]
    wanted += [ALONGSIDE, DEFAULT_DIRECTORY]

    seen = []
    for where in wanted:
        if where not in seen:
            seen.append(where)
    return tuple(seen)


def identify(image, catalogue=None):
    """Which part this image is, or why it is not one the manifest knows."""
    digest = hashlib.sha256(image).hexdigest()
    entries = (catalogue or manifest())["artifacts"]

    for entry in entries:
        for accepted in entry["accepted"]:
            if accepted["sha256"] == digest:
                return Identity(
                    part=entry["part"],
                    processor=entry["processor"],
                    revision=accepted["revision"],
                    program_words=entry["programWords"],
                    data_words=entry["dataWords"],
                )

    raise Unrecognised(_diagnosis(image, digest, entries))


def _diagnosis(image, digest, entries):
    same_length = [entry for entry in entries if entry["bytes"] == len(image)]

    if same_length:
        parts = ", ".join(entry["part"] for entry in same_length)
        return (
            f"this is {len(image)} bytes, the length of {parts}, but its content is altered:"
            f" its sha256 is {digest} and no accepted revision has that."
            " A file of the right length with the wrong content is usually a different"
            " revision than the one it is named after, or a bad dump"
        )

    lengths = ", ".join(sorted({str(entry["bytes"]) for entry in entries})) or "none"
    return (
        f"this is {len(image)} bytes, and the manifest knows no part of that length"
        f" (it knows {lengths}). Its sha256 is {digest}."
        " A file much larger than any of those is usually an archive rather than the"
        " image inside it, and one slightly larger usually carries a header"
    )


def load(chip, image, identity=None):
    """Put an image into a processor, program first and table second."""
    program_words = identity.program_words if identity else len(chip.stores.program)
    data_words = identity.data_words if identity else len(chip.stores.table)
    wanted = program_words * PROGRAM_BYTES_PER_WORD + data_words * TABLE_BYTES_PER_WORD

    if len(image) != wanted:
        raise WrongShape(
            f"a {chip.model.name} takes {wanted} bytes of firmware and this is {len(image)}"
        )

    split = program_words * PROGRAM_BYTES_PER_WORD
    chip.stores.load_program(image[:split])
    chip.stores.load_table(image[split:])
    return chip


def found(where=None, catalogue=None):
    """Every image the manifest recognises in one directory, with its file."""
    where = Path(where) if where is not None else directory()
    if not where.is_dir():
        return

    for path in sorted(where.iterdir()):
        if path.suffix.lower() not in READABLE_SUFFIXES or not path.is_file():
            continue
        try:
            yield identify(path.read_bytes(), catalogue), path
        except Unrecognised:
            continue


def search(places=None, catalogue=None):
    """The same across every place that is searched, the first copy of each part winning."""
    seen = set()
    for where in places if places is not None else directories():
        for identity, path in found(where, catalogue):
            if identity.part in seen:
                continue
            seen.add(identity.part)
            yield identity, path
