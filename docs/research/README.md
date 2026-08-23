# Engineering records

Dated records from building this kit — measurements, decisions, and reviews written as the
work happened. They are kept deliberately, and they are **not** documentation: nothing here
tells you how to use the kit. For that, start at the [README](../../README.md).

They are here because this pack's claim is that a measured, self-reviewing workflow produces
better software than an unmeasured one, and the honest way to support that claim is to publish
what the workflow actually caught. So these files include the times it caught us:

- a defect we diagnosed from documentation, prescribed a fix for, and then **refuted by testing** —
  the prescribed fix would have broken a working install
- a divergence metric used to plan a large port that turned out to be **unable to size it**, because
  it could not separate an upstream advance from a deliberate edit of our own
- several reports whose own numbers were wrong, found by reviewing the report rather than the code

Each file states where its verification stops. Where a claim is unverified it says so, and where a
later record supersedes an earlier one the earlier one is corrected in place rather than deleted.

There is deliberately **no per-file index here.** The filenames are the index: each is
`YYYY-MM-DD` plus its subject, so the directory sorts chronologically and reads by topic without a
list that has to be maintained. This program has already paid twice for hand-written lists that rot
— a skill count in four places and a commit count that was stale before the commit landed — and a
twenty-row index of research notes would be the third. If navigation ever needs more than filenames,
generate it.

Read them as evidence, not as instructions. If a record and the code disagree, the code is right
and the record has aged — every file carries the date it was true.
