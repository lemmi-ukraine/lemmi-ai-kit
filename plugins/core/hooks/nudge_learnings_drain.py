"""SessionStart nudge: say once, when a session opens, that the learnings buffer is due for a drain or
that no retrospective has run for a while.

It is OFF until a project turns it on. When it is on it prints at most one line per arm into the
session, and it has two arms. The drain arm prints

  intake at {N} entries, last drain {D} days ago -> run /lemmi-ai-kit-core:learning-consolidator

and only when the buffer is due: it holds MORE than 25 entries, or it holds any and the last drain is
7 or more days old. The retrospective arm prints one of

  no retrospective in {D} days -> run /lemmi-ai-kit-core:session-retrospective
  no retrospective recorded -> run /lemmi-ai-kit-core:session-retrospective

the first when the newest report is 14 days old or more, the second when there is none. An arm that
is not due prints nothing. Both due is one reply holding both lines, the drain line first. Neither
due prints nothing at all.

Why. The buffer-pressure check in `task-learnings` and the cadence guard in `learning-consolidator`
say the same thing, but only when those skills run, so a session that ends without either never shows
it and the buffer can pass the threshold unseen. This hook says it at the one moment every session
has, the start. The retrospective arm is the same idea for `session-retrospective`, whose own cadence
guard also speaks only when that skill runs. It only says: it never blocks and never writes a file.

THE SWITCH. `.ai/drain-nudge-hook.json` in the project folder: `CLAUDE_PROJECT_DIR`, or the `cwd` of
the payload when the variable is absent. The file is read at every session start, so nothing is cached
and a change needs no restart. It is a JSON object with one optional key:

  enabled   true switches the hook on. Absent or false: the hook prints nothing at all. Any value
            that is not a boolean makes the file unusable, as below. (default false)

A file the hook cannot use (not UTF-8 JSON, not an object, an unknown key, a value of the wrong
type) never blocks and never passes in silence: nothing else is checked, and one `systemMessage`
says what is wrong with the file.

WHAT IT READS. The buffer, `.ai/learnings.md`: the count is the lines that start with `### `, the
number `lint learnings --list-entries` prints (a heading inside a code fence is counted there, so it
is counted here). The last drain, `.ai/ai-changelog.md`: a `CONSOLIDATION` entry whose
`- **Drained:** N` count is above 0; an entry without the line, or with a count that cannot be read,
counts as drained, so a changelog written before the marker keeps working. The entry's date is the
`## YYYY-MM-DD` heading it sits under. An entry under any other heading cannot be dated and is
skipped, as is a heading or entry inside a code fence (the changelog documents its own format in
fences), the same as in the lint. The newest date wins whatever order the sections are in. With no
drain recorded the age arm stays quiet, and a buffer over the entry threshold still speaks and says
`no drain recorded`. A file that cannot be read is never an error: a missing buffer is silence for the
drain arm, a missing changelog is no drain recorded.

The retrospective arm reads the names in `.ai/retrospectives/`, where `session-retrospective` writes
`{date}-retrospective.md`. A name that starts with `YYYY-MM-DD` and is a real day dates a report, and
the newest date wins. The modification time is never read, because a copy or a checkout gives every
file one. A name that starts with no date is ignored, and a date after today counts as today. A
folder that is missing, empty or without a dated name means no retrospective is recorded. A folder
that cannot be listed (the path is a file, for example) is a failure of this arm alone: it prints
nothing, the drain arm is not affected, and the exit code stays 0.

THE THREE NUMBERS, 25 and 7 for the drain arm and 14 for the retrospective arm. The first two are the
ones `task-learnings` (the buffer-pressure check) and `learning-consolidator` (the cadence guard)
state, and 14 is the default window of `session-retrospective`. A hook is one file that imports only
the standard library, so this file holds its own copy, and a test reads the three skills and the
README and fails when any of them disagrees: change a number in all of them together.

WHAT IT DELIBERATELY DOES NOT DO. It reads no stash, branch or backup, and a project cannot move any
of the three numbers. It runs nothing: a line only names the command. The registration covers the
`startup`, `resume` and `clear` sources of a session start and leaves out `compact`, because a
compaction continues the conversation that already saw the line (reasoned, not tried).

NOT ESTABLISHED. The hooks reference says that a SessionStart hook's plain stdout and its
`additionalContext` are added to Claude's context. In the part read, it does not say whether the
operator sees them, so whether the line reaches the operator depends on Claude relaying it, and that
was not tried live. It does not say whether a SessionStart `systemMessage` is shown to the user,
which the warning above relies on. It does say that Claude's first response waits for SessionStart
hooks, so every session start pays one launcher start whether or not the switch is on.

Contract: reads the SessionStart payload on stdin and prints either one JSON object (the nudge, or the
warning about the switch file) or nothing. It exits 0 in every case, and a payload it cannot use, a
file it cannot read, or a bug in the scan is silence: a hook that crashes must not get in the way of
a session. A failure in the retrospective arm costs that arm alone, and the drain arm's line is still
printed.
"""

import json
import os
import re
import sys
from collections.abc import Iterator, Mapping
from datetime import date
from typing import Any, cast

CONFIG_PARTS = (".ai", "drain-nudge-hook.json")
CONFIG_KEYS = ("enabled",)
LEARNINGS_PARTS = (".ai", "learnings.md")
CHANGELOG_PARTS = (".ai", "ai-changelog.md")
RETROSPECTIVES_PARTS = (".ai", "retrospectives")

# The numbers `task-learnings`, `learning-consolidator` and `session-retrospective` state; a test
# fails when this file and they disagree.
PRESSURE_ABOVE = 25  # the buffer holds MORE than this many entries
DUE_AFTER_DAYS = 7  # the last drain is at least this many days old
RETROSPECTIVE_AFTER_DAYS = 14  # the newest report is at least this many days old

ROUTE = "run /lemmi-ai-kit-core:learning-consolidator"
RETROSPECTIVE_ROUTE = "run /lemmi-ai-kit-core:session-retrospective"
DRAIN_ENTRY_TYPE = "CONSOLIDATION"
DRAINED_FIELD = "Drained"

# The buffer's count: the lines `lint learnings --list-entries` counts.
ENTRY_RE = re.compile(r"^### ", re.MULTILINE)

# The date a report's file name opens with. The hook's own: the lint holds no copy of it.
REPORT_DAY_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")

# Copied from the lint, so the changelog is read as the lint reads it; a test fails when one differs.
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
DATE_HEADING_RE = re.compile(r"^## (\d{4})-(\d{2})-(\d{2})\s*$")
TYPE_TAG_RE = re.compile(r"^([A-Z][A-Z-]+):")
FIELD_RE = re.compile(r"^- \*\*(.+?):?\*\*:?\s*(.*)$")
DRAINED_COUNT_RE = re.compile(r"^\d+(?:\s|$)")


# ----------------------------------------------------------------------------------- the switch


def load_switch(project_dir: str) -> tuple[bool, list[str]]:
    """Whether the project's switch file turns the hook on, and what is wrong with the file.

    (False, []) when there is no file, (False, problems) when it cannot be used. Read on every call.
    """
    path = os.path.join(project_dir, *CONFIG_PARTS)
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except (FileNotFoundError, NotADirectoryError):
        return False, []
    except OSError as error:
        return False, [f"it cannot be read ({type(error).__name__})"]
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        return False, ["it is not UTF-8 text"]
    except RecursionError:
        return False, ["it is nested too deeply"]
    except ValueError as error:
        return False, [f"it is not valid JSON ({str(error)[:80]})"]
    if not isinstance(data, dict):
        return False, ["the top level must be a JSON object"]
    fields = cast(dict[str, Any], data)  # the keys of a JSON object are always strings
    problems: list[str] = []
    unknown = sorted(key for key in fields if key not in CONFIG_KEYS)
    if unknown:
        problems.append("unknown key(s): " + ", ".join(unknown[:5]))
    enabled = fields.get("enabled", False)
    if not isinstance(enabled, bool):
        problems.append("enabled must be true or false")
    if problems:
        return False, problems
    return enabled is True, []


# --------------------------------------------------------------------------------- the two files


def _read(project_dir: str, parts: tuple[str, ...]) -> str | None:
    """A project file as the lint reads it (a byte order mark dropped, bytes that are not UTF-8
    replaced), or None when it cannot be read."""
    try:
        with open(os.path.join(project_dir, *parts), "rb") as handle:
            return handle.read().decode("utf-8-sig", errors="replace")
    except OSError:
        return None


def count_entries(text: str) -> int:
    """The `### ` headings at the start of a line: the count `lint learnings --list-entries` prints."""
    return len(ENTRY_RE.findall(text))


def _heading_day(line: str) -> date | None:
    match = DATE_HEADING_RE.match(line)
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _entries(text: str) -> Iterator[tuple[date | None, str, list[str]]]:
    """Every `### ` entry as (the date of its section, its title, its body lines).

    A line inside a code fence is example text and never a heading, but it stays in the body of the
    entry it sits in. An entry above the first section, or under a heading that is not a real date,
    has no date. The headings are tested with `startswith`, not with the lint's patterns for them:
    those end in a lazy group before `\\s*$`, which a line of many spaces turns quadratic.
    """
    day: date | None = None
    title: str | None = None
    body: list[str] = []
    inside = False
    for line in text.splitlines():
        fence = FENCE_RE.match(line) is not None
        if fence:
            inside = not inside
        if fence or inside:
            if title is not None:
                body.append(line)
            continue
        if line.startswith("## ") and len(line) > 3:
            if title is not None:
                yield day, title, body
                title = None
            day = _heading_day(line)
        elif line.startswith("### ") and len(line) > 4:
            if title is not None:
                yield day, title, body
            title, body = line[4:], []
        elif title is not None:
            body.append(line)
    if title is not None:
        yield day, title, body


def _counts_as_drain(title: str, body: list[str]) -> bool:
    """A `CONSOLIDATION` entry whose `Drained` count is above 0, or that states no readable count."""
    tag = TYPE_TAG_RE.match(title)
    if tag is None or tag.group(1) != DRAIN_ENTRY_TYPE:
        return False
    value = None
    for line in body:
        match = FIELD_RE.match(line.strip())
        if match is not None and match.group(1).rstrip(":") == DRAINED_FIELD:
            value = match.group(2)
            break
    if value is None or DRAINED_COUNT_RE.match(value.strip()) is None:
        return True
    try:
        return int(value.split()[0]) > 0
    except ValueError:  # more digits than int() converts: a count, and not a small one
        return True


def last_drain(text: str) -> date | None:
    """The date of the newest drain in the changelog, or None when none is recorded."""
    return max(
        (
            day
            for day, title, body in _entries(text)
            if day is not None and _counts_as_drain(title, body)
        ),
        default=None,
    )


# ------------------------------------------------------------------------- the retrospectives


def _report_day(name: str) -> date | None:
    """The day a file name starts with (`YYYY-MM-DD`), or None when it starts with no real day."""
    match = REPORT_DAY_RE.match(name)
    if match is None:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:  # a month 13, a 30th of February, a year 0
        return None


def newest_report(project_dir: str) -> date | None:
    """The date of the newest report in `.ai/retrospectives/`, or None when there is none.

    The date is the one the file name starts with, never the modification time. A folder that is not
    there, or that holds no dated name, is no report. A folder that cannot be listed raises: that is
    a failure of the arm, which its caller turns into silence, and is not the same as no report.
    """
    try:
        names = os.listdir(os.path.join(project_dir, *RETROSPECTIVES_PARTS))
    except FileNotFoundError:
        return None
    return max(
        (day for day in map(_report_day, names) if day is not None), default=None
    )


# ----------------------------------------------------------------------------------- the reply


def nudge_line(entries: int, drained_on: date | None, today: date) -> str | None:
    """The one line to print, or None when the buffer is not due."""
    age = None if drained_on is None else max(0, (today - drained_on).days)
    stale = entries > 0 and age is not None and age >= DUE_AFTER_DAYS
    if entries <= PRESSURE_ABOVE and not stale:
        return None
    since = "no drain recorded" if age is None else f"last drain {age} days ago"
    return f"intake at {entries} entries, {since} -> {ROUTE}"


def retrospective_line(newest: date | None, today: date) -> str | None:
    """The one line to print, or None when the newest report is recent enough."""
    if newest is None:
        return f"no retrospective recorded -> {RETROSPECTIVE_ROUTE}"
    age = max(0, (today - newest).days)
    if age < RETROSPECTIVE_AFTER_DAYS:
        return None
    return f"no retrospective in {age} days -> {RETROSPECTIVE_ROUTE}"


def _warning(problems: list[str]) -> str:
    text = "; ".join(problems)[:600]
    return (
        f"drain-nudge hook: {'/'.join(CONFIG_PARTS)} is not usable ({text}); the buffer was not "
        "checked this session. Fix the file, or delete it to switch the hook off."
    )


def _drain_arm(project: str, today: date) -> str | None:
    """The drain arm's line: None when the buffer cannot be read or is not due."""
    buffer = _read(project, LEARNINGS_PARTS)
    if buffer is None:
        return None
    changelog = _read(project, CHANGELOG_PARTS)
    drained_on = None if changelog is None else last_drain(changelog)
    return nudge_line(count_entries(buffer), drained_on, today)


def _retrospective_arm(project: str, today: date) -> str | None:
    """The retrospective arm's line. Any failure here is silence for this arm and for no other."""
    try:
        return retrospective_line(newest_report(project), today)
    except Exception:  # fail open: a folder that cannot be listed, or a bug in this arm
        return None


def decide(raw: bytes, environ: Mapping[str, str], today: date | None = None) -> str:
    """The text to print on stdout for one payload: the nudge (a line per arm that is due), a
    warning, or nothing at all."""
    try:
        payload: Any = json.loads(raw.decode("utf-8-sig", errors="replace"))
    except Exception:  # fail open: a payload that cannot be read is silence
        return ""
    if not isinstance(payload, dict):
        return ""
    cwd = cast(dict[str, Any], payload).get("cwd")
    project = environ.get("CLAUDE_PROJECT_DIR") or cwd
    if not isinstance(project, str) or not project or "\x00" in project:
        return ""
    enabled, problems = load_switch(project)
    if problems:
        return json.dumps({"systemMessage": _warning(problems)})
    if not enabled:
        return ""
    day = today or date.today()
    lines = [
        line
        for line in (_drain_arm(project, day), _retrospective_arm(project, day))
        if line is not None
    ]
    if not lines:
        return ""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            }
        }
    )


def main() -> None:
    try:
        out = decide(sys.stdin.buffer.read(), os.environ)
        if out:
            sys.stdout.write(out)  # ASCII only: json.dumps escapes everything else
            sys.stdout.flush()
    except Exception:  # fail open: a bug here must never get in the way of a session
        return


if __name__ == "__main__":
    main()
