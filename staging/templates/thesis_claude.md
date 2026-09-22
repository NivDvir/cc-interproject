# Doctoral Thesis

Working notes for the thesis. LaTeX source, BibTeX references, and the analysis code
that produces every figure in the manuscript.

The rule for this repository: nothing in `figures/` is edited by hand. Every figure is
the output of a script in `analysis/`, and every script is deterministic given a seed.

## Repository layout

| Directory | Contents | Edited by hand |
|---|---|---|
| `chapters/` | One `.tex` file per chapter | Yes |
| `analysis/` | Python that produces figures and tables | Yes |
| `figures/` | Generated PDF and PNG figures | No |
| `tables/` | Generated LaTeX table fragments | No |
| `data/raw/` | Immutable source data | No |
| `data/derived/` | Cached intermediate results | No |
| `refs/` | BibTeX files exported from the reference manager | No |
| `build/` | Compiler output | No |

## Building

The whole document builds with one command:

```bash
just build
```

That runs `latexmk -pdf -interaction=nonstopmode main.tex` after regenerating any
figure whose inputs changed. A clean rebuild takes about four minutes.

To rebuild a single chapter while writing:

```bash
just chapter 3
```

This compiles `chapters/03-methods.tex` against the shared preamble and opens the
result. It skips the bibliography pass, so citations will show as question marks.

## Regenerating figures

Each figure has a script named after it. The convention is strict:

```
analysis/fig_<number>_<slug>.py  ->  figures/fig_<number>_<slug>.pdf
```

A script reads only from `data/raw/` and `data/derived/`, and writes only its own
figure. If a script needs a new intermediate result, it writes it into `data/derived/`
under a name that includes the parameters that produced it.

```python
from pathlib import Path

DERIVED = Path("data/derived")


def cache_path(name: str, seed: int, window: int) -> Path:
    return DERIVED / f"{name}-seed{seed}-w{window}.parquet"
```

Never write into `data/raw/`. That directory is a copy of the deposited dataset and
must stay byte-identical to it so the archive checksum keeps matching.

## Chapter status

| Chapter | Title | Draft | Supervisor read | Final |
|---|---|---|---|---|
| 1 | Introduction | Yes | Yes | No |
| 2 | Background | Yes | Yes | No |
| 3 | Methods | Yes | No | No |
| 4 | Study one | Yes | No | No |
| 5 | Study two | Partial | No | No |
| 6 | Study three | No | No | No |
| 7 | General discussion | No | No | No |

Chapter 6 is blocked on the second round of data collection, which is scheduled after
the ethics amendment is approved.

## Writing conventions

- One sentence per line in the `.tex` sources. Diffs are unreadable otherwise.
- No manual line breaks inside a sentence.
- Cross-references use `\cref`, never a bare `\ref`.
- Every figure has a caption that can be read on its own, without the body text.
- British spelling throughout, including in figure labels.
- Numbers below ten are written as words unless they carry a unit.

## Citation hygiene

References are exported from the reference manager into `refs/library.bib` and are
never edited in place. If a record is wrong, fix it in the manager and re-export.

The check that catches most mistakes:

```bash
just check-refs
```

It reports citation keys used in the text but missing from the bibliography, entries
in the bibliography that nothing cites, and any entry missing a DOI or a URL.

## Statistics

The analysis is pre-registered. The pre-registration is in `docs/preregistration.md`
and is the authority on which tests are confirmatory.

Anything not in that document is exploratory and must be reported as exploratory, in
its own subsection, with no inferential claim attached.

| Study | Design | N planned | N collected | Primary test |
|---|---|---|---|---|
| One | Within-subject | 48 | 51 | Repeated-measures ANOVA |
| Two | Between-subject | 120 | 118 | Mixed-effects model |
| Three | Within-subject | 60 | 0 | Repeated-measures ANOVA |

Effect sizes are reported with 95 percent confidence intervals. A p-value never
appears without the effect size next to it.

## Reproducibility

The environment is pinned. Recreate it with:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
```

The lock file is generated from `requirements.in` with `pip-compile`. Do not add a
package by hand to the lock file.

Every analysis script takes a `--seed` argument and defaults to 20240115. A figure
produced with a different seed must say so in its caption.

## Data protection

The raw data contain participant identifiers. They are pseudonymised at collection
time and the key never enters this repository.

- Do not copy anything from `data/raw/` into a chapter or a commit message.
- Do not include participant free-text responses in a figure.
- The share of the dataset that may be deposited publicly is listed in
  `docs/deposit-manifest.md`. Nothing outside that list leaves the machine.

## Submission checklist

1. Every chapter marked final in the table above.
2. `just build` clean, with no overfull boxes over 5pt.
3. `just check-refs` reporting nothing.
4. Figure list and table list regenerated.
5. Word count within the faculty limit, excluding appendices.
6. Declaration signed and dated.
7. Archive deposited and the checksum recorded in `docs/deposit-manifest.md`.

## Open questions

- Whether study two's exclusion criteria should be reported in the methods chapter or
  in the study chapter. The supervisor prefers the methods chapter.
- Whether the appendix tables should be landscape. They fit in portrait at 9pt but are
  hard to read.
- Whether to move the pilot study into an appendix. It answers a question the final
  design abandoned, so it may confuse more than it helps.

## Things not to do

- Do not run a formatter over the `.tex` sources. It destroys the one-sentence-per-line
  convention and makes every later diff useless.
- Do not commit anything from `build/`. It is large and regenerable.
- Do not renumber chapters. The file names carry the numbers and the cross-references
  follow the labels, not the file names, so a renumbering silently breaks both.
- Do not change the citation style. The faculty template fixes it.

## Backups

The repository is mirrored nightly to the university storage. The mirror is a copy,
not a working tree, so a change made there is lost at the next sync.

The deposited archive is separate and is only written at submission time.

## Collaborators

| Person | Role | Reads drafts | Has repository access |
|---|---|---|---|
| Primary supervisor | Supervision | Yes | Yes |
| Second supervisor | Statistics | Chapters 3 to 6 | No |
| Lab technician | Data collection | No | Raw data only |

A draft goes to the second supervisor as a PDF, never as a repository link, because
the raw data directory is mounted inside the working tree.

## Glossary

Terms used throughout the chapters with a narrower meaning than usual:

- **Trial**: one presentation of one stimulus to one participant.
- **Block**: a run of trials sharing a condition, separated by a rest screen.
- **Session**: everything one participant did on one day.
- **Run**: one execution of an analysis script, identified by its seed.
