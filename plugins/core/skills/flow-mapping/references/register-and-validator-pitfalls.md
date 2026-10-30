# Register and validator pitfalls

Three ways a flow-document edit looks finished and is not. Each is a check to run before calling
an edit done, not a statement about the validator's internals.

**An edit that drops a call edge, or cites a new file, cascades into other tables.** The validator
ties the Symbol index, the Call graph and the Coverage table together: a symbol row's `called by`
and scenarios must equal what the edges and the scenario paths say, and a file named in an evidence
cell needs a Coverage row. When an edit removes an edge, delete the callee's Symbol index row in the
same edit. Cite in an evidence cell only files that already have a Coverage row, or add the row. A
validator that prints zero findings may be blind to the region it was asked about: before quoting
its zero, run it on a deliberately broken copy of the document and see it report the break.

**A cell that is itself one backtick span cannot take backticked names.** An evidence cell built
from a `code:` span and a `test:` span ends its span at the first inner backtick and leaves the rest
as plain text between two broken spans. Read a cell's quoting grammar in the live document before
applying a spec's replacement text; where the cell is one span, write the names without backticks
and list that as a deliberate deviation in the hand-off.

**Coverage-note counts are pinned records.** A figure in a Coverage note is pinned to the commit it
was counted at, and other cells may sum it, so a later layer does not overwrite it: it appends a
`Re-measured at layer X` note beside the old figure. The derived rows a layer will change can be
named without regenerating anything in the shared tree: generate each derived artifact from the
layer's base export and from its changed export, scratch copies only, and diff the two outputs.
Prove a "no difference" with a control that must differ.
