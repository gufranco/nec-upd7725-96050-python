from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import stack
from upd7725 import MODELS

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

HERE = Path(__file__).resolve().parent

RECORD = HERE / "testroms.json"

MEASURED = HERE / "testroms_measured.json"

PROGRAM_BYTES = 3

TABLE_BYTES = 2

WITHIN = "within"

BEYOND = "beyond"

UNBOUNDED = "unbounded"

RECORDING = "--record"

Measures = dict[str, dict[str, Any]]


def model_for(size: int) -> str | None:
    for name, part in sorted(MODELS.items()):
        if part.program_words * PROGRAM_BYTES + part.table_words * TABLE_BYTES == size:
            return name
    return None


def _reversed_words(body: bytes, width: int) -> bytes:
    return b"".join(body[at : at + width][::-1] for at in range(0, len(body), width))


def reordered(image: bytes, model: str) -> bytes:
    split = MODELS[model].program_words * PROGRAM_BYTES
    program = _reversed_words(image[:split], PROGRAM_BYTES)
    return program + _reversed_words(image[split:], TABLE_BYTES)


def verdict(found: stack.Census, levels: int) -> str:
    if not found.bounded:
        return UNBOUNDED
    return WITHIN if found.deepest <= levels else BEYOND


def measure(image: bytes) -> dict[str, Any] | None:
    model = model_for(len(image))
    if model is None:
        return None
    found = stack.census(stack.program_of(image, model) or [], model)
    return {
        "model": model,
        "reached": found.reached,
        "fromReset": found.from_reset,
        "fromInterrupt": found.from_interrupt,
        "enablesInterrupts": found.enables_interrupts,
        "deepest": found.deepest,
        "recursive": list(found.recursive),
        "indirect": list(found.indirect),
        "verdict": verdict(found, MODELS[model].stack_levels),
    }


def examine(image: bytes, entry: dict[str, Any]) -> dict[str, Any] | None:
    model = model_for(len(image))
    if model is None:
        return None
    dumped = stack.digest(image) == entry["sha256"] != entry["canonicalSha256"]
    canonical = reordered(image, model) if dumped else image
    found = measure(canonical) or {}
    return {**found, "canonicalMatches": stack.digest(canonical) == entry["canonicalSha256"]}


def listed(record: Path) -> dict[str, dict[str, Any]]:
    known: dict[str, dict[str, Any]] = {}
    for entry in json.loads(record.read_text())["cartridges"]:
        known[entry["sha256"]] = entry
        known[entry["canonicalSha256"]] = entry
    return known


def measured_in(folder: Path, record: Path) -> Measures:
    known = listed(record)
    found: Measures = {}
    for path in sorted(one for one in folder.iterdir() if one.is_file()):
        image = path.read_bytes()
        entry = known.get(stack.digest(image))
        result = None if entry is None else examine(image, entry)
        if entry is not None and result is not None:
            found[entry["id"]] = result
    return found


def disagreements(found: Measures, held: dict[str, Any]) -> list[str]:
    problems = []
    for name, result in sorted(found.items()):
        if held.get(name) != result:
            problems.append(f"{name}: measured {result}, recorded {held.get(name)}")
        if result["verdict"] == BEYOND:
            problems.append(f"{name}: needs {result['deepest']} levels, more than the part has")
        if not result["canonicalMatches"]:
            problems.append(f"{name}: reordered, it is not the image the record names")
    return problems


def main(
    argv: Sequence[str],
    say: Callable[[str], object] = print,
    record: Path = RECORD,
    measured: Path = MEASURED,
) -> int:
    folders = [one for one in argv if one != RECORDING]
    total = len(json.loads(record.read_text())["cartridges"])
    if not folders:
        say(f"  0 of {total} test images examined: no folder named, so none was checked")
        return 0
    found = measured_in(Path(folders[0]), record)
    say(f"  {len(found)} of {total} test images examined")
    if RECORDING in argv:
        measured.write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
        say(f"  recorded into {measured.name}")
        return 0
    problems = disagreements(found, json.loads(measured.read_text()))
    for one in problems:
        say(f"  ! {one}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
