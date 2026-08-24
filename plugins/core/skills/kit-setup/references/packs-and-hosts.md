# Packs, hosts, and the commands to print

Everything Step 2 needs to print a correct recommendation and nothing more. The
skill detects and recommends; it does not install. Print from here, verbatim.

## The packs

| Plugin | Ships | Recommend when |
|---|---|---|
| `lemmi-ai-kit-core` | the language-agnostic workflow: setup, spec-driven development, post-task review, the learnings loop, orchestration, research, review | always — it is already installed, or the user could not be reading this |
| `lemmi-ai-kit-python` | Python coding and testing conventions | `pyproject.toml`, `setup.cfg`, or top-level `*.py` |

**That is the whole catalogue.** There is no pack for Go, Rust, TypeScript, Java
or anything else, and the honest answer when one is asked for is that nobody has
written it — not that setup is incomplete. The core pack is language-agnostic by
construction, so a project in an unpacked language loses nothing that exists.

Whoever wants one writes it: `docs/authoring-a-pack.md` in the kit's repository
is the path from an empty directory to a merged pack, and `new-pack` scaffolds
the skeleton. **Update the table above when a pack lands** — this file is what
the skill reads, so a pack absent here is a pack the skill never recommends.

## Which host

Codex sets **both** `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT`; Claude Code sets only
the second. So the test is `PLUGIN_ROOT` first, and the natural order — check the
Claude variable, and if it is set assume Claude — reports every Codex session as
Claude Code.

```bash
if [ -n "${PLUGIN_ROOT:-}" ]; then KIT_HOST=codex; else KIT_HOST=claude; fi
```

## The commands to print

Two commands per pack: add the marketplace once, then install each pack. Print
the pair for the detected host. **Do not run them.**

### Claude Code

In-session, which is where the user already is:

```
/plugin marketplace add lemmi-ukraine/lemmi-ai-kit
/plugin install lemmi-ai-kit-python@lemmi
```

From a terminal:

```sh
claude plugin marketplace add lemmi-ukraine/lemmi-ai-kit
claude plugin install lemmi-ai-kit-python@lemmi
```

### Codex

```sh
codex plugin marketplace add lemmi-ukraine/lemmi-ai-kit
codex plugin add lemmi-ai-kit-python@lemmi
```

Note `plugin add`, not `plugin install`. The two clients differ on the verb as
well as on the source syntax below.

### If `owner/repo` does not resolve

That shorthand has **not been exercised** against this repository on either
client. Say so when you print it, and give the fallback in the same breath
rather than waiting for it to fail:

```sh
git clone https://github.com/lemmi-ukraine/lemmi-ai-kit
cd lemmi-ai-kit
```

Then, and this is the part that is not cosmetic:

```sh
codex plugin marketplace add .      # Codex: a bare dot
claude plugin marketplace add ./    # Claude Code: a trailing slash
```

**Claude Code rejects `.` outright** with `Invalid marketplace source format`.
Each spelling above is the one actually run against that client on 2026-08-23;
neither has been shown to work on the other. Print the line for the detected
host and do not offer the other as an alternative.

## Telling the user it worked

`plugin list` reporting the plugin as installed is weaker evidence than it
looks — a probe of this kit showed a client reporting a plugin as installed
while it carried no manifest at all. Ask for the inventory **by name**:

```sh
claude plugin details lemmi-ai-kit-python
```

And say the thing users get wrong: **the new skills are not live in this
session.** They load on the next one, whatever the install output says.
