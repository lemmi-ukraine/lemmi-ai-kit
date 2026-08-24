"""GitHub issue forms: they parse, and they carry the structure GitHub requires.

Nothing in this suite read `.github/ISSUE_TEMPLATE/` before. That directory is the one
place in the repo where a syntax error fails nowhere a maintainer looks: GitHub does
not reject a malformed issue form, it silently stops rendering it, and the contributor
gets the blank-issue box instead. The repository loses the structured report it asked
for, CI stays green, and the only signal is an absence nobody is watching. Four files
were maintained by hand against a schema no local check knew about.

**PyYAML is not a dependency of this project and this module does not add one.** It
parses a deliberately restricted subset of YAML, and stating that subset's limits
exactly is half the point of the file -- an instrument whose limits are undocumented is
how this program got the measurement problems it has.

## What the parser DOES model

Block mappings, block sequences, plain and quoted scalars, `true`/`false`, `null`,
single-line flow sequences of scalars (`labels: ["bug"]`), literal and folded block
scalars (`value: |`), whole-line `#` comments, and a leading `---` marker. That is
every construct the files in this directory use.

## What it does NOT model -- and it RAISES rather than guessing

Anchors (`&`), aliases (`*`), tags (`!`), flow mappings (`{...}`), explicit keys (`?`),
multi-document streams, quoted mapping keys, backslash escapes inside quoted scalars,
a quote nested in a quoted scalar, tab indentation, a UTF-8 BOM, and a duplicate key
within one mapping. A file using any of those fails this test even where GitHub would
accept it. That false alarm is deliberate: it is loud and it is fixable, and the
alternative is a parser that silently disagrees with GitHub about what a file means --
the same class of defect as the silent non-render this module exists to catch.

## What it deliberately does NOT catch

- **Anything past structure.** Not whether a URL resolves, whether a label reads well,
  whether a dropdown offers the right options, or whether any of the prose is true. A
  form that parses and is entirely wrong-headed passes every test here.
- **YAML 1.1 booleans other than `true`/`false`.** GitHub reads `yes`, `no`, `on` and
  `off` as booleans; this parser leaves them strings, so `required: yes` fails the
  boolean assertion below rather than being accepted. Write `true`.
- **Folding of `>` block scalars.** Their text is kept verbatim rather than folded.
  Nothing compares such a value to anything -- only its non-emptiness is asserted --
  so the unfolded form cannot produce a wrong answer, only an unused one.
- **Numbers.** A scalar that looks numeric stays a string. Nothing here needs one.
- **GitHub's server-side limits** -- field counts, total body size, whether a label in
  `labels:` exists in the repository, whether an assignee has write access.
- **Anything across files.** Two forms may carry the same `name`; only `id` uniqueness
  *within* one form is checked, because that is the rule GitHub enforces.

## Where the element rules knowingly differ from GitHub's published reference

Two places, in opposite directions, both recorded here rather than left for someone to
rediscover from a confusing failure:

- **Stricter:** a `markdown` element carrying an `id` or a `validations` block is
  rejected. GitHub's syntax reference documents neither as supported there. If it in
  fact tolerates them, this fails loudly on a form that renders -- the same trade this
  module takes everywhere else.
- **Looser:** `validations: {required: ...}` on a `checkboxes` element is accepted,
  though the reference documents no `validations` for that type (per-option `required`
  is the mechanism). Being wrong in the strict direction here would redden the suite
  over a form GitHub renders fine, so this one is left permissive on purpose.

Neither shape appears in the four files today, so both are statements about the next
form somebody writes, not about anything shipped.

## The parser was checked against a real one before being trusted

A hand-rolled parser is itself an instrument, and an unverified instrument is the
thing this repo keeps getting caught by. So it was diffed against PyYAML 6.0.3 in a
throwaway `uvx --from pyyaml` environment -- not a dependency, and not run by this
suite -- over every file in this directory plus every synthetic form below. All of
them parsed to structurally identical trees. The refusal cases split as the sections
above claim: tabs, an unterminated quote, an over-indented key, a bare non-key line
and a second document are refused by both; a BOM, a duplicate key, a flow mapping, a
tag, an anchor and an empty document are refused only here. Redo it the same way if
the parser is ever changed -- and note that the four files are CRLF on disk, so
`read_text`'s universal-newline translation is load-bearing.

## The scan surface is asserted, not assumed

`test_the_scan_surface_matches_git` fixes the file set this module reads against
`git ls-files`, so an enumeration that stops seeing files fails instead of passing on
an empty set. `test_the_two_schemas_partition_the_directory` asserts the form set and
the config set are disjoint and together cover every file present -- a file matching
neither is a failure, not a silent skip.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FORMS_DIR_RELATIVE = ".github/ISSUE_TEMPLATE"
_FORMS_DIR = _REPO_ROOT / _FORMS_DIR_RELATIVE

# `config.yml` is a DIFFERENT schema, and is separated deliberately rather than by
# accident: it carries no `name` and no `body`, so applying the form contract to it
# would fail a file that is correct. GitHub fixes this filename, which is why it is a
# literal here instead of a heuristic like "the one with no body" -- a heuristic would
# quietly reclassify a BROKEN form as a config and stop checking it.
_CONFIG_NAME = "config.yml"


# --- the restricted parser ------------------------------------------------------------


class _SubsetError(ValueError):
    """YAML outside the subset this parser models. Raised, never guessed past."""


_KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)[ \t]*:(?:[ \t]+(.*))?\Z")
_BLOCK_SCALAR_RE = re.compile(r"\A[|>][+-]?\Z")

# Indicators that open a construct this parser does not model, named so the failure
# says what to remove rather than only where.
_UNSUPPORTED_HEADS: dict[str, str] = {
    "&": "an anchor",
    "*": "an alias",
    "!": "a tag",
    "{": "a flow mapping",
    "?": "an explicit key",
    "@": "a reserved indicator",
    "`": "a reserved indicator",
}


class _Reader:
    """A line-at-a-time reader over one document. Fails closed on unmodelled syntax."""

    def __init__(self, text: str, where: str) -> None:
        if text.startswith("\ufeff"):
            raise _SubsetError(f"{where}:1: starts with a UTF-8 BOM")
        self._where = where
        self._lines = text.split("\n")
        self._i = 0

    def _fail_at(self, index: int, message: str) -> NoReturn:
        raise _SubsetError(f"{self._where}:{index + 1}: {message}")

    def _significant(self) -> tuple[int, int, str] | None:
        """(index, indent, content) of the next line carrying syntax, or None at EOF.

        The returned line is NOT consumed; blank lines and whole-line comments before
        it are, because nothing downstream ever needs them.
        """
        while self._i < len(self._lines):
            raw = self._lines[self._i]
            body = raw.strip()
            if not body or body.startswith("#"):
                self._i += 1
                continue
            lead = raw[: len(raw) - len(raw.lstrip())]
            if "\t" in lead:
                self._fail_at(self._i, "tab in the indentation; YAML forbids it")
            return (self._i, len(lead), raw[len(lead) :].rstrip())
        return None

    @staticmethod
    def _is_item(content: str) -> bool:
        return content == "-" or content.startswith("- ")

    def document(self) -> Any:
        head = self._significant()
        if head is None:
            self._fail_at(0, "the document is empty")
        index, indent, content = head
        if content == "---":
            self._i = index + 1
            head = self._significant()
            if head is None:
                self._fail_at(index, "the document is empty after its `---` marker")
            index, indent, content = head
        if indent != 0:
            self._fail_at(index, f"the document starts indented by {indent}")
        value = self._block(0)
        trailing = self._significant()
        if trailing is not None:
            self._fail_at(
                trailing[0],
                f"content after the end of the document: {trailing[2]!r} "
                "(a multi-document stream is outside the subset this parser models)",
            )
        return value

    def _block(self, indent: int) -> Any:
        head = self._significant()
        if head is None:  # pragma: no cover - every caller checks first
            return None
        if self._is_item(head[2]):
            return self._sequence(indent)
        return self._mapping(indent)

    def _mapping(
        self, indent: int, first: tuple[int, str] | None = None
    ) -> dict[str, Any]:
        """A block mapping whose keys sit at `indent`.

        `first` carries the `key: value` that followed a `- ` on a sequence-item line
        and has already been consumed; every later key of that item sits at `indent`.
        """
        result: dict[str, Any] = {}
        pending = first
        while True:
            if pending is None:
                head = self._significant()
                if head is None:
                    break
                index, line_indent, content = head
                if line_indent < indent:
                    break
                if line_indent > indent:
                    self._fail_at(
                        index, f"indented by {line_indent} where {indent} was expected"
                    )
                if self._is_item(content):
                    self._fail_at(
                        index, "a sequence item where a mapping key was expected"
                    )
                self._i = index + 1
            else:
                index, content = pending
                pending = None
            match = _KEY_RE.match(content)
            if match is None:
                self._fail_at(index, f"not a mapping key: {content!r}")
            key = match.group(1)
            if key in result:
                self._fail_at(index, f"duplicate key {key!r} in the same mapping")
            raw_value = match.group(2)
            if raw_value is None:
                result[key] = self._nested(indent)
            elif _BLOCK_SCALAR_RE.match(raw_value):
                result[key] = self._block_scalar(indent)
            else:
                result[key] = self._scalar(index, raw_value)
        return result

    def _nested(self, parent_indent: int) -> Any:
        """The value of a key that carried none on its own line."""
        head = self._significant()
        if head is None:
            return None
        _, indent, content = head
        if indent > parent_indent:
            return self._block(indent)
        # A sequence may sit at its key's own indent; a mapping may not.
        if indent == parent_indent and self._is_item(content):
            return self._sequence(parent_indent)
        return None

    def _sequence(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while True:
            head = self._significant()
            if head is None:
                break
            index, line_indent, content = head
            if line_indent < indent:
                break
            if line_indent > indent:
                self._fail_at(
                    index,
                    f"indented by {line_indent} where sequence items sit at {indent}",
                )
            if not self._is_item(content):
                break
            after = content[1:]
            spaces = len(after) - len(after.lstrip(" "))
            rest = after[spaces:]
            self._i = index + 1
            if not rest:
                items.append(self._nested(indent))
            elif _KEY_RE.match(rest):
                items.append(self._mapping(indent + 1 + spaces, first=(index, rest)))
            else:
                items.append(self._scalar(index, rest))
        return items

    def _scalar(self, index: int, raw: str) -> Any:
        text = raw.strip()
        if not text or text in {"null", "~"}:
            return None
        head = text[0]
        if head in _UNSUPPORTED_HEADS:
            self._fail_at(
                index,
                f"{_UNSUPPORTED_HEADS[head]} is outside the subset this parser models",
            )
        if head == "[":
            if not text.endswith("]"):
                self._fail_at(index, f"unterminated flow sequence: {text!r}")
            inner = text[1:-1].strip()
            if not inner:
                return []
            if any(ch in inner for ch in "[]{}"):
                self._fail_at(index, "a nested flow collection is outside the subset")
            return [self._scalar(index, part) for part in inner.split(",")]
        if head in "\"'":
            return self._unquote(index, text)
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        return text

    def _unquote(self, index: int, text: str) -> str:
        quote = text[0]
        if len(text) < 2 or not text.endswith(quote):
            self._fail_at(index, f"unterminated quoted scalar: {text!r}")
        body = text[1:-1]
        if quote == '"' and "\\" in body:
            self._fail_at(
                index, "a backslash escape in a quoted scalar is outside the subset"
            )
        if quote in body:
            self._fail_at(
                index, f"a {quote} inside a quoted scalar is outside the subset"
            )
        return body

    def _block_scalar(self, parent_indent: int) -> str:
        """A `|` or `>` block, kept verbatim. `>` folding is NOT applied -- see above."""
        collected: list[str] = []
        block_indent: int | None = None
        while self._i < len(self._lines):
            raw = self._lines[self._i]
            if not raw.strip():
                collected.append("")
                self._i += 1
                continue
            lead = raw[: len(raw) - len(raw.lstrip())]
            if "\t" in lead:
                self._fail_at(self._i, "tab in the indentation; YAML forbids it")
            if len(lead) <= parent_indent:
                break
            if block_indent is None:
                block_indent = len(lead)
            collected.append(raw[min(block_indent, len(lead)) :].rstrip())
            self._i += 1
        while collected and not collected[-1]:
            collected.pop()
        return "\n".join(collected)


def _parse(text: str, where: str) -> Any:
    return _Reader(text, where).document()


# --- the schema GitHub enforces -------------------------------------------------------

# Top-level keys GitHub accepts in an issue FORM. An unrecognised one is a failure
# rather than an ignored extra: `lables:` is exactly the hand-edit that renders a form
# without its labels and reports nothing.
_FORM_TOP_LEVEL: frozenset[str] = frozenset(
    {"name", "description", "title", "labels", "assignees", "projects", "body"}
)

# Per element type: the attributes GitHub accepts, and the subset it requires.
_ELEMENT_ATTRIBUTES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "markdown": (frozenset({"value"}), frozenset({"value"})),
    "input": (
        frozenset({"label", "description", "placeholder", "value"}),
        frozenset({"label"}),
    ),
    "textarea": (
        frozenset({"label", "description", "placeholder", "value", "render"}),
        frozenset({"label"}),
    ),
    "dropdown": (
        frozenset({"label", "description", "multiple", "options", "default"}),
        frozenset({"label", "options"}),
    ),
    "checkboxes": (
        frozenset({"label", "description", "options"}),
        frozenset({"label", "options"}),
    ),
}

_ITEM_KEYS: frozenset[str] = frozenset({"type", "id", "attributes", "validations"})
_ID_RE = re.compile(r"\A[A-Za-z0-9_-]+\Z")

# `config.yml` accepts exactly these two, and no `body`.
_CONFIG_TOP_LEVEL: frozenset[str] = frozenset({"blank_issues_enabled", "contact_links"})
_CONTACT_KEYS: frozenset[str] = frozenset({"name", "url", "about"})


def _as_list(value: Any) -> list[Any]:
    """A list value, restated as `list[Any]` for the type checker."""
    return list(value)


def _text(value: Any) -> str | None:
    """`value` when it is a non-blank string, else None. Blank is never acceptable."""
    return value if isinstance(value, str) and value.strip() else None


def _form_problems(where: str, document: Any) -> list[str]:
    """Every way `document` departs from the issue-form schema. Never raises."""
    if not isinstance(document, dict):
        return [f"{where}: the document is not a mapping ({type(document).__name__})"]
    form = cast(dict[str, Any], document)
    problems: list[str] = []

    unknown = sorted(set(form) - _FORM_TOP_LEVEL)
    if unknown:
        problems.append(
            f"{where}: unrecognised top-level key(s) {unknown} -- GitHub accepts "
            f"{sorted(_FORM_TOP_LEVEL)}"
        )
    for required in ("name", "description"):
        if _text(form.get(required)) is None:
            problems.append(f"{where}: `{required}` is missing or empty")
    if _text(form.get("title", "-")) is None:
        problems.append(f"{where}: `title` is present but empty")
    for listed in ("labels", "assignees", "projects"):
        value = form.get(listed)
        if value is None:
            continue
        if not isinstance(value, list) or not all(
            _text(entry) for entry in _as_list(value)
        ):
            problems.append(f"{where}: `{listed}` must be a list of non-empty strings")

    body = form.get("body")
    if not isinstance(body, list) or not body:
        problems.append(
            f"{where}: `body` must be a non-empty list -- a form without one renders "
            "as nothing at all"
        )
        return problems

    seen_ids: dict[str, int] = {}
    for position, raw_item in enumerate(_as_list(body), 1):
        problems += _element_problems(
            f"{where}: body[{position}]", position, raw_item, seen_ids
        )
    return problems


def _element_problems(
    where: str, position: int, raw: Any, seen_ids: dict[str, int]
) -> list[str]:
    if not isinstance(raw, dict):
        return [f"{where}: not a mapping ({type(raw).__name__})"]
    item = cast(dict[str, Any], raw)
    problems: list[str] = []

    unknown = sorted(set(item) - _ITEM_KEYS)
    if unknown:
        problems.append(f"{where}: unrecognised key(s) {unknown}")

    kind = _text(item.get("type"))
    if kind is None or kind not in _ELEMENT_ATTRIBUTES:
        return problems + [
            f"{where}: `type` is {item.get('type')!r}; GitHub accepts "
            f"{sorted(_ELEMENT_ATTRIBUTES)}"
        ]
    allowed, required = _ELEMENT_ATTRIBUTES[kind]

    identifier = item.get("id")
    if identifier is not None:
        if kind == "markdown":
            problems.append(f"{where}: a `markdown` element takes no `id`")
        text = _text(identifier)
        if text is None or _ID_RE.match(text) is None:
            problems.append(f"{where}: `id` {identifier!r} must match {_ID_RE.pattern}")
        elif text in seen_ids:
            problems.append(
                f"{where}: `id` {text!r} repeats body[{seen_ids[text]}] -- GitHub "
                "requires ids unique within a form"
            )
        else:
            seen_ids[text] = position

    attributes = item.get("attributes")
    if not isinstance(attributes, dict):
        problems.append(f"{where}: `attributes` must be a mapping")
    else:
        attrs = cast(dict[str, Any], attributes)
        extra = sorted(set(attrs) - allowed)
        if extra:
            problems.append(
                f"{where}: `{kind}` has no attribute(s) {extra} -- it accepts "
                f"{sorted(allowed)}"
            )
        for name in sorted(required):
            if name == "options":
                continue
            if _text(attrs.get(name)) is None:
                problems.append(f"{where}: `attributes.{name}` is missing or empty")
        if "options" in required:
            problems += _option_problems(where, kind, attrs.get("options"))

    validations = item.get("validations")
    if validations is not None:
        if kind == "markdown":
            problems.append(f"{where}: a `markdown` element takes no `validations`")
        if not isinstance(validations, dict):
            problems.append(f"{where}: `validations` must be a mapping")
        else:
            checks = cast(dict[str, Any], validations)
            extra = sorted(set(checks) - {"required"})
            if extra:
                problems.append(f"{where}: unrecognised validation(s) {extra}")
            if "required" in checks and not isinstance(checks["required"], bool):
                problems.append(
                    f"{where}: `validations.required` is {checks['required']!r}; it "
                    "must be the bare literal true or false"
                )
    return problems


def _option_problems(where: str, kind: str, options: Any) -> list[str]:
    if not isinstance(options, list) or not options:
        return [f"{where}: `attributes.options` must be a non-empty list"]
    problems: list[str] = []
    for position, option in enumerate(_as_list(options), 1):
        at = f"{where}.options[{position}]"
        if kind == "dropdown":
            if _text(option) is None:
                problems.append(
                    f"{at}: a dropdown option must be a non-empty string, not "
                    f"{option!r} (quote it if it contains a colon)"
                )
            continue
        if not isinstance(option, dict):
            problems.append(f"{at}: a checkbox option must be a mapping with a `label`")
            continue
        entry = cast(dict[str, Any], option)
        extra = sorted(set(entry) - {"label", "required"})
        if extra:
            problems.append(f"{at}: unrecognised key(s) {extra}")
        if _text(entry.get("label")) is None:
            problems.append(f"{at}: `label` is missing or empty")
        if "required" in entry and not isinstance(entry["required"], bool):
            problems.append(
                f"{at}: `required` is {entry['required']!r}; it must be the bare "
                "literal true or false"
            )
    return problems


def _config_problems(where: str, document: Any) -> list[str]:
    if not isinstance(document, dict):
        return [f"{where}: the document is not a mapping ({type(document).__name__})"]
    config = cast(dict[str, Any], document)
    problems: list[str] = []

    if "body" in config:
        problems.append(
            f"{where}: carries a `body`. This file is the chooser configuration, not "
            "a form -- a form here would never render"
        )
    unknown = sorted(set(config) - _CONFIG_TOP_LEVEL - {"body"})
    if unknown:
        problems.append(
            f"{where}: unrecognised key(s) {unknown} -- GitHub accepts "
            f"{sorted(_CONFIG_TOP_LEVEL)}"
        )
    if "blank_issues_enabled" in config and not isinstance(
        config["blank_issues_enabled"], bool
    ):
        problems.append(
            f"{where}: `blank_issues_enabled` is {config['blank_issues_enabled']!r}; "
            "it must be the bare literal true or false"
        )

    links = config.get("contact_links")
    if links is None:
        return problems
    if not isinstance(links, list) or not links:
        return problems + [f"{where}: `contact_links` must be a non-empty list"]
    for position, raw in enumerate(_as_list(links), 1):
        at = f"{where}: contact_links[{position}]"
        if not isinstance(raw, dict):
            problems.append(f"{at}: not a mapping")
            continue
        link = cast(dict[str, Any], raw)
        missing = sorted(_CONTACT_KEYS - set(link))
        if missing:
            problems.append(f"{at}: missing {missing}")
        extra = sorted(set(link) - _CONTACT_KEYS)
        if extra:
            problems.append(f"{at}: unrecognised key(s) {extra}")
        for name in sorted(_CONTACT_KEYS & set(link)):
            if _text(link[name]) is None:
                problems.append(f"{at}: `{name}` is empty")
        url = _text(link.get("url"))
        if url is not None and not url.startswith(("http://", "https://")):
            problems.append(f"{at}: `url` {url!r} is not an absolute http(s) URL")
    return problems


# --- the scan surface -----------------------------------------------------------------


def _present_files() -> list[str]:
    """Every file in the issue-template directory, as a name. Not filtered by suffix."""
    return sorted(p.name for p in _FORMS_DIR.iterdir() if p.is_file())


def _git_tracked_names() -> list[str]:
    """The same set according to git, as an independent second probe."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", _FORMS_DIR_RELATIVE],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:  # pragma: no cover - not a work tree
        pytest.fail("not a git work tree, so the tracked set cannot be checked")
    return sorted(
        entry.rsplit("/", 1)[-1]
        for entry in result.stdout.decode("utf-8").split("\0")
        if entry
    )


def _form_names() -> list[str]:
    return [name for name in _present_files() if name != _CONFIG_NAME]


def _read(name: str) -> str:
    return (_FORMS_DIR / name).read_text(encoding="utf-8")


# --- the guards -----------------------------------------------------------------------


def test_the_scan_surface_matches_git() -> None:
    """A zero here is not a finding, so prove both probes see the same non-zero set.

    The directory listing and `git ls-files` are independent enumerations. If they
    disagree, either an untracked file is being checked as though it shipped, or a
    tracked one is being skipped -- and a skip is how this gap existed at all.
    """
    present = _present_files()
    assert present, (
        f"{_FORMS_DIR_RELATIVE} is empty or missing; nothing would be checked"
    )
    assert present == _git_tracked_names(), (
        "the directory listing and git disagree about what lives in "
        f"{_FORMS_DIR_RELATIVE}: on disk {present}, tracked {_git_tracked_names()}"
    )
    assert _CONFIG_NAME in present, (
        f"{_CONFIG_NAME} is gone, so the second schema below is checked against "
        "nothing and its half of this module passes vacuously"
    )


def test_the_two_schemas_partition_the_directory() -> None:
    """The two scan surfaces must be disjoint and must together cover everything.

    A file matching neither schema is a failure, not a silent skip -- GitHub also
    supports legacy markdown templates in this directory, and one appearing here
    should make somebody extend this module deliberately rather than slip past it.
    """
    present = set(_present_files())
    forms = set(_form_names())
    config = {_CONFIG_NAME} & present

    assert not (forms & config), (
        f"a file is in both scan surfaces: {sorted(forms & config)}"
    )
    assert forms | config == present, (
        f"files in {_FORMS_DIR_RELATIVE} that neither schema claims: "
        f"{sorted(present - forms - config)}"
    )
    assert forms, "no issue forms found, so the form contract below checks nothing"
    assert all(name.endswith((".yml", ".yaml")) for name in present), (
        f"a non-YAML file is in {_FORMS_DIR_RELATIVE}: {sorted(present)}. This module "
        "parses everything it finds; decide deliberately what to do with it."
    )


def test_every_file_parses() -> None:
    """The minimum bar: nothing here is syntactically broken.

    See the module docstring for the exact subset. A construct outside it fails here
    with a message naming the construct, not with a pass.
    """
    for name in _present_files():
        try:
            _parse(_read(name), f"{_FORMS_DIR_RELATIVE}/{name}")
        except _SubsetError as exc:
            pytest.fail(str(exc))


def test_every_form_matches_the_issue_form_schema() -> None:
    problems: list[str] = []
    for name in _form_names():
        where = f"{_FORMS_DIR_RELATIVE}/{name}"
        problems += _form_problems(where, _parse(_read(name), where))
    assert not problems, "issue forms GitHub would not render:\n" + "\n".join(problems)


def test_the_chooser_config_matches_its_own_schema() -> None:
    """`config.yml` is the other schema, checked on purpose rather than skipped."""
    where = f"{_FORMS_DIR_RELATIVE}/{_CONFIG_NAME}"
    problems = _config_problems(where, _parse(_read(_CONFIG_NAME), where))
    assert not problems, f"{_CONFIG_NAME} is malformed:\n" + "\n".join(problems)


# --- positive controls ----------------------------------------------------------------
#
# A guard nobody has watched refuse is an assumption. Each block below feeds a known-bad
# input to the SAME function the guards above call, and fails if it comes back clean.

_A_GOOD_FORM = """\
name: Bug report
description: Something is wrong
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Read this first.
  - type: input
    id: what
    attributes:
      label: What broke?
    validations:
      required: true
  - type: dropdown
    id: host
    attributes:
      label: Where?
      options:
        - Claude Code
        - Codex
    validations:
      required: false
  - type: checkboxes
    id: checks
    attributes:
      label: Before submitting
      options:
        - label: I searched existing issues
          required: false
"""

_UNPARSEABLE: dict[str, str] = {
    "tab indentation": "name: x\nbody:\n\t- type: input\n",
    "a duplicate key": "name: x\nname: y\nbody: []\n",
    "a flow mapping": "name: x\nbody: {a: 1}\n",
    "an anchor": "name: &a x\nbody: []\n",
    "an alias": "name: x\nother: *a\n",
    "a tag": "name: !!str x\nbody: []\n",
    "a line that is not a key": "name: x\nthis line has no colon\n",
    "a second document": "name: x\nbody: []\n---\nname: y\n",
    "an over-indented key": "name: x\nbody: []\n    stray: 1\n",
    "a UTF-8 BOM": "\ufeffname: x\nbody: []\n",
    "an empty document": "\n# only a comment\n",
    "an unterminated quote": 'name: "x\nbody: []\n',
}

_BROKEN_FORMS: dict[str, str] = {
    "no name": _A_GOOD_FORM.replace("name: Bug report\n", ""),
    "an empty name": _A_GOOD_FORM.replace("name: Bug report", 'name: ""'),
    "no description": _A_GOOD_FORM.replace("description: Something is wrong\n", ""),
    "no body at all": _A_GOOD_FORM.split("body:")[0],
    "an empty body": _A_GOOD_FORM.split("body:")[0] + "body: []\n",
    "a misspelled top-level key": _A_GOOD_FORM.replace("labels:", "lables:"),
    "a misspelled element type": _A_GOOD_FORM.replace("type: input", "type: inupt"),
    "a misspelled attribute": _A_GOOD_FORM.replace(
        "label: What broke?", "lable: What broke?"
    ),
    "an input with no label": _A_GOOD_FORM.replace("      label: What broke?\n", ""),
    "markdown with no value": _A_GOOD_FORM.replace(
        "      value: |\n        Read this first.\n", "      label: nope\n"
    ),
    "a duplicate id": _A_GOOD_FORM.replace("id: host", "id: what"),
    "an id with a space": _A_GOOD_FORM.replace("id: what", 'id: "what now"'),
    "a quoted boolean": _A_GOOD_FORM.replace("required: true", 'required: "true"'),
    "a dropdown with no options": _A_GOOD_FORM.replace(
        "      options:\n        - Claude Code\n        - Codex\n", ""
    ),
    "a checkbox option that is a bare string": _A_GOOD_FORM.replace(
        "        - label: I searched existing issues\n          required: false\n",
        "        - I searched existing issues\n",
    ),
    "validations on a markdown block": _A_GOOD_FORM.replace(
        "  - type: input\n", "    validations:\n      required: true\n  - type: input\n"
    ),
}

_BROKEN_CONFIGS: dict[str, str] = {
    "a body": "blank_issues_enabled: true\nbody:\n  - type: input\n",
    "a misspelled key": "blank_issues_ebabled: true\n",
    "a quoted boolean": 'blank_issues_enabled: "true"\n',
    "a contact link with no url": "contact_links:\n  - name: x\n    about: y\n",
    "a relative url": "contact_links:\n  - name: x\n    url: SECURITY.md\n    about: y\n",
    "an empty about": "contact_links:\n  - name: x\n    url: https://e.test\n    about: ''\n",
}


@pytest.mark.parametrize("why", sorted(_UNPARSEABLE))
def test_the_parser_refuses_what_it_cannot_model(why: str) -> None:
    """Positive control for the parser: each of these must RAISE, not parse.

    Half are YAML errors GitHub would also reject; half are constructs this parser
    deliberately does not model. Both must fail loudly, because a parser that guesses
    is worse than no parser -- it would report a structure the file does not have.
    """
    with pytest.raises(_SubsetError):
        _parse(_UNPARSEABLE[why], f"<{why}>")


def test_the_parser_reads_a_good_form_correctly() -> None:
    """Guard the guard: prove the parser produces the structure, not just no error.

    Without this, every check above could pass on a parser that returned an empty
    mapping for everything -- and `_form_problems` would then report the emptiness as
    the form's fault, on files that are fine.
    """
    document = _parse(_A_GOOD_FORM, "<good>")
    assert document["name"] == "Bug report"
    assert document["labels"] == ["bug"]
    body = document["body"]
    assert [element["type"] for element in body] == [
        "markdown",
        "input",
        "dropdown",
        "checkboxes",
    ]
    assert body[0]["attributes"]["value"] == "Read this first."
    assert body[1]["validations"]["required"] is True
    assert body[2]["attributes"]["options"] == ["Claude Code", "Codex"]
    assert body[3]["attributes"]["options"] == [
        {"label": "I searched existing issues", "required": False}
    ]
    assert _form_problems("<good>", document) == []


@pytest.mark.parametrize("why", sorted(_BROKEN_FORMS))
def test_the_form_check_catches_a_broken_form(why: str) -> None:
    """Positive control for the schema: each mutation of a good form must be reported.

    The mutations are the hand-edits that actually happen -- a dropped key, a
    transposed letter, a quoted boolean -- and each one silently stops the form
    rendering on GitHub. If one of these ever comes back clean, the schema check has a
    hole exactly the size of that mutation.
    """
    text = _BROKEN_FORMS[why]
    try:
        document = _parse(text, f"<{why}>")
    except _SubsetError:
        return  # refused at the parser, which is also a catch
    assert _form_problems(f"<{why}>", document), (
        f"a form with {why} was reported clean; the schema check does not cover it"
    )


@pytest.mark.parametrize("why", sorted(_BROKEN_CONFIGS))
def test_the_config_check_catches_a_broken_config(why: str) -> None:
    """Positive control for the second schema, including the form/config mix-up."""
    text = _BROKEN_CONFIGS[why]
    try:
        document = _parse(text, f"<{why}>")
    except _SubsetError:
        return
    assert _config_problems(f"<{why}>", document), (
        f"a config with {why} was reported clean; the config check does not cover it"
    )


def test_the_two_schemas_are_not_interchangeable() -> None:
    """Applying either contract to the other file must fail, or they are one contract.

    If `_config_problems` accepted a form, then routing a broken form to it -- which
    is what a filename typo does -- would stop checking it and report nothing.
    """
    good_form = _parse(_A_GOOD_FORM, "<good>")
    real_config = _parse(_read(_CONFIG_NAME), _CONFIG_NAME)

    assert _config_problems("<form-as-config>", good_form), (
        "the config contract accepts an issue form, so the two are not distinct"
    )
    assert _form_problems("<config-as-form>", real_config), (
        "the form contract accepts the chooser config, so the two are not distinct"
    )
