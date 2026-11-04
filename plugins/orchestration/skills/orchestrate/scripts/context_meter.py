"""Print how large one Claude Code session's context is, read from its transcript file.

This is a meter, not a usage guard: this script never stops or advises. It reads the one file
it is given, writes nothing and starts no process; what a reading means is the reader's call.

    python context_meter.py TRANSCRIPT [--window TOKENS]

After a first line saying what this is, it prints:
  context_tokens     input + cache creation + cache read tokens of the last main-thread
                     assistant record whose usage total is above zero (sub-agent records are
                     skipped, so a helper's larger prompt never stands for the session)
  percent_of_window  context_tokens as a percent of TOKENS; NOT GIVEN without it, never guessed
  tool_calls         distinct tool_use ids in main-thread records (a replayed id counts once)

Exit 0 only when it measured. A file it cannot read, a line that is not a JSON object, a usage
block with absent fields or no usage record prints "NOT MEASURED: <reason>" and exits 2: no
reading is not a zero reading. No transcript text is printed, only line numbers.
"""

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import cast

NOTICE = "context meter: a reading, not a usage guard; it never stops or advises."
NO_USAGE = "no main-thread assistant record with usage above zero (a sub-agent's file holds only sub-agent records)"
FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _object(value: object) -> dict[str, object] | None:
    """The value as a JSON object, or None when it is anything else."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def measure(lines: Iterable[str]) -> tuple[int, int]:
    """Context tokens and distinct tool calls of the main thread; ValueError when it cannot say."""
    context: int | None = None
    calls: set[str] = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = _object(json.loads(line))
        except ValueError:
            record = None
        if record is None:
            raise ValueError(f"line {number} is not a JSON object")
        if record.get("isSidechain") is True:
            continue
        message = _object(record.get("message")) or {}
        blocks = message.get("content")
        for block in cast("list[object]", blocks) if isinstance(blocks, list) else []:
            entry = _object(block) or {}
            ident = entry.get("id")
            if entry.get("type") == "tool_use" and isinstance(ident, str):
                calls.add(ident)
        usage = _object(message.get("usage"))
        if record.get("type") == "assistant" and usage is not None:
            sizes = [usage.get(name) for name in FIELDS]
            ints = [n for n in sizes if isinstance(n, int) and not isinstance(n, bool)]
            if len(ints) != len(FIELDS):
                raise ValueError(f"line {number}: usage fields absent or not integers")
            total = sum(ints)
            if total > 0:  # an all-zero block is a placeholder record, not a reading
                context = total
    if context is None:
        raise ValueError(NO_USAGE)
    return context, len(calls)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument("transcript", type=Path, help="a .jsonl transcript")
    parser.add_argument("--window", type=int, metavar="TOKENS", help="window size")
    args = parser.parse_args(argv)
    window = cast("int | None", args.window)
    if window is not None and window <= 0:
        parser.error("--window must be a positive number of tokens")
    print(NOTICE)
    try:
        with cast("Path", args.transcript).open(encoding="utf-8") as handle:
            context, calls = measure(handle)
    except (OSError, ValueError) as error:
        reason = error.strerror if isinstance(error, OSError) else str(error)
        print(f"NOT MEASURED: {reason or type(error).__name__}")
        return 2
    shown = "NOT GIVEN" if window is None else f"{100 * context / window:.1f}"
    print(f"context_tokens: {context}\npercent_of_window: {shown}\ntool_calls: {calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
