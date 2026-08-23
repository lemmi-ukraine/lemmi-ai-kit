# The pack split — install-level review

**Dated:** 2026-08-23, two commits after the split landed.
**Reviews:** the core/python pack split, at install level rather than test level.
**Method:** install both packs from the local marketplace into an isolated configuration
directory, then compare what *materialises* against both the checkout and the manifest **by name**,
not by count. Read-only throughout: no file in the checkout was modified, and the working tree's
dirty set was byte-identical before and after.

Install-level was chosen over the test suite deliberately. An earlier fixture in this program showed
a plugin host accepting a plugin with **no manifest at all** and reporting it installed, with the
version silently degraded to `"local"`. Any check that reads "install succeeded" as "the pack is
correct" is unsound, so nothing below rests on an exit code.

---

## 1. The split is correct

| Assertion | core | python |
|---|---|---|
| installed set == checkout `plugins/<pack>/skills/` | 35 | 2 |
| installed set == `manifest.toml`, mapped profile → pack | 35 | 2 |
| tracked in git but **not** shipped | 0 | 0 |
| cross-pack name collision | none | none |

37 skills materialise in total, matching the manifest and the count the README derives. The version
reported is `0.1.0` — **the degrade-to-`"local"` failure does not reproduce** on the host tested.
Manifest validation passes for the marketplace and both packs, but that is recorded as a fact, not
as evidence; the table above is the evidence.

Running the CLI from inside the installed core payload resolves correctly — the repository root is
found via the plugin-manifest branch, available packs resolve to `('core',)`, and the manifest loads
35 entries. So the `src/` tree inside the payload is not bloat: with no publish pipeline, it is how
the CLI reaches an adopter at all.

**One consequence worth stating for anyone writing migration notes:** a core-only adopter's `list`
shows **35**, not 37. The number depends on which packs are installed, so no document should promise
37 unconditionally.

## 2. Installing a plugin packages the working tree, not the git tree

This is the finding. Diffing the shipped payload against `git ls-files plugins/core`:

```
tracked  107
shipped  117
```

Ten extra files, of which two were artefacts of this review's own probe. The remaining **eight were
never in git**:

```
src/lemmi_ai_kit/__pycache__/{__init__,__main__,checks,cli,manifest,scaffold}.cpython-311.pyc
src/lemmi_ai_kit/assets/ai/templates/test-cases.md
src/lemmi_ai_kit/assets/ai/templates/test-plan.md
```

Six are ignored bytecode, in no commit and reviewed by no one. Two are uncommitted template drafts
that simply happened to be in the tree when the install ran. Nothing tracked was *missing* from
either pack, so the leak is one-directional and silent — an install looks complete because it is
complete, plus extra.

The mechanism does not care what the extra files are. It copies the directory. Any secret, backup,
or half-finished draft sitting under `plugins/` at the moment of packaging reaches whoever installs.
The `python` pack leaked nothing, but that is not a control holding — nothing untracked happened to
be sitting under it.

**The control this implies:** require `git status --porcelain plugins/` to be **empty** before any
install or publish an adopter will consume, and prefer a pre-publish check that refuses to package
while untracked or ignored files exist under `plugins/`. This belongs with the packaging governance,
not with the split, which is why it is filed here rather than as a restructure defect.

## 3. The built wheel carries no skills — latent, and stated as latent

|  | before the split | after |
|---|---|---|
| `packages =` | `["src/lemmi_ai_kit"]` | `["plugins/core/src/lemmi_ai_kit"]` |
| where skills live | *inside* that tree | `plugins/*/skills/` — **outside** it |
| `SKILL.md` in the wheel | 38 | **0** |

Built and installed into a clean virtual environment: no pack roots resolve, no skill directories
are found, and loading the manifest raises `no plugin skill roots found`. `list` and `scaffold` both
exit 2.

**No adopter reaches this.** There is no publish pipeline, and the adoption guide states the kit
adds nothing to `pip install`. The defect is that building still *succeeds* and emits a silently
broken artefact. The fix is to remove the wheel target or make it fail loudly; either is small, and
neither is urgent.

This is recorded at low severity on purpose. A packaging change that cannot reach a user is not the
same class of problem as §2, and flattening the two would misdirect whoever reads this next.

## 4. Confirmed, not new

The skill-fleet audit exits **0** on an empty skills directory. This was already a known open
trade-off — the complete fix changes exit codes for adopters who have no local skills — and this
review adds only a live reproduction from an installed artefact, not a new finding.

## 5. The command an adopter runs to see what materialised

```
claude plugin marketplace add ./
claude plugin install lemmi-ai-kit-core@lemmi
claude plugin details lemmi-ai-kit-core
```

`plugin details` prints the component inventory **by name** — `Skills (35) agent-delegate,
ai-changelog, …` — which is what makes it a verification step rather than a reassurance.

Two details worth carrying into any install documentation: the marketplace source must be `./`, as
a bare `.` is rejected as an invalid source format; and the equivalent documented elsewhere for the
other host uses the bare `.` form, so the two are not interchangeable.

## 6. Where this verification stops

- **Only the local install path was exercised.** The `owner/repo` source form cannot be tested while
  the repository is private, and the second host's CLI was not present on the machine used. A "real
  install" is therefore demonstrated for the local path **only**, and the public path remains
  untested by construction until the repository is published. Whatever check runs at that moment is
  the first and only exercise of it.
- **This review would not have caught stale references outside the packs.** It compares what
  materialises per pack. A file that reaches contributors through the repository rather than through
  a payload — a pull-request template, for instance — is entirely outside its scope. That gap needs
  its own guard; this method does not subsume it.
- **The two probe-created files** excluded from §2's count were bytecode this review's own import
  generated inside the payload. They are named here rather than silently dropped, because a count
  that quietly excludes something is the kind of number this program has already been burned by.
