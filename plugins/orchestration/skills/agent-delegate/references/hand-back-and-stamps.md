# Hand-back reports and dated stamps

Two ways a delegated report, or a stamped hand-off, ends up recording something that did not happen.

**Save the hand-back report verbatim, at once, labelled as model output.** A sub-agent's report is
the only full copy of its findings. Write it unedited, next to the record, the moment it arrives. A
digest is not a durable copy: it is where misstatements enter, so pair each digested finding with
the report's own words. A sub-agent's own transcript file can come back empty; the report then
survives in the parent session's transcript as a record that contains the agent id. Extract it from
there rather than rebuilding it from the digest.

**Write "done", "last" or "re-stamped" only after the action.** In a prompt, hand-off or record with
dated blocks, a sentence that says the stamp was refreshed has to be written after the refresh. Take
the clock reading (`date -u`) immediately before the stamp edit and make that edit the last write;
take it again after any later patch. The rule covers every write that carries a time, not only a
stamp edit (a board entry, a label, a header's "updated" time): the same slip has been seen outside
stamp edits. When one reading cannot pin the time, write the bound between two clock readings,
never a guessed minute or a masked label. Correct a guessed stamp with a script that asserts exactly
one match per replacement and prints how many it made. A command that fails when a timestamp cited
in the document is later than the stamp would catch this mechanically; it is not built here.
