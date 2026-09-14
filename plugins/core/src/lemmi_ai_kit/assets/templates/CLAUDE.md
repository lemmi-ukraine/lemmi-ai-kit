# CLAUDE.md
@AGENTS.md

## Skills

This is a catalog, not an installation record. Invoke only skills from enabled
plugins in the host's inventory. Install an optional pack through the native plugin
manager when its workflow is needed; this file does not activate it.

### User-Invocable (use with `/skill-name`)
{{SKILLS_USER}}

### Auto-Loaded by Claude (background knowledge)
{{SKILLS_AUTO}}

### Internal Pipeline Skills (invoked by workflows or directly by the model; hidden from the `/` menu)
{{SKILLS_INTERNAL}}
