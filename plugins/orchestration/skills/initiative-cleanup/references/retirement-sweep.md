# Retirement sweep — the ids a retired file defined

Step 4b repoints every reference to a retired file by its path or basename. A path grep cannot see
an id: text relocated out of the file can still say "see REQ-12" or "per DEC-3" after the file that
said what those ids are has gone, and no build fails over an id nobody can resolve.

Run this after the content has landed in its destination (a README, a test, a code comment, the
forward plan) and before the file is removed.

1. **Derive the id prefixes from the retired file**, not from memory. List the id-shaped tokens it
   contains, keep the letters before the number, and drop what is not an id (`UTF`, `SHA`):

   ```bash
   grep -oE '[A-Z]{1,5}-?[0-9]+' <retired file> | sed -E 's/-?[0-9]+$//' | sort -u
   ```

2. **Destination grep.** Search every destination for those prefixes, in files of every type:

   ```bash
   git grep --untracked --no-exclude-standard -I -n -E '(REQ|DEC)-?[0-9]+' -- <destination paths>
   ```

3. **Write what each id means where it now stands.** Each hit either gets a clause that says what
   the id required, decided or measured, or is replaced by the thing it named. A bare id is a
   pointer to a hole: the retired file was the only place that could resolve it. Re-run the
   destination grep; a hit still bare is not done.
