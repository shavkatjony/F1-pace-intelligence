# Working notes (raw)

This folder is the project's lab notebook. Unlike [`docs/`](../docs/README.md), nothing here is
polished: it keeps the research, the trial and error, the failed attempts, the problems and the
first plans as they were written at the time. It is here on purpose, to show how the project
got to the decisions in `docs/decisions/`, including what didn't work.

| Folder | What goes in it |
|---|---|
| `plans/` | the plans written before and during the project ([00-rules-and-purpose.md](plans/00-rules-and-purpose.md): the first rules page, plan v4, 5 October 2026) |
| `research/` | questions explored, sources read, other projects compared |
| `trials/` | things tried: what I did, what happened, what I learned |
| `failures/` | what broke or didn't work, and how it was found and fixed |
| `reports/` | raw outputs and first drafts of reports |
| `journal/` | dated working notes, day by day |

## Adding a note

Name it `YYYY-MM-DD-short-title.md`, so the folder reads in time order. A useful shape for a
trial or a failure:

```markdown
# <date> · <what I tried>
What I tried:
What happened (numbers, errors, screenshots):
What I learned:
What I did next (a link to the decision record or commit, if there is one):
```

The notes are personal and may be wrong or out of date; the decision records and the method
are the reference.
