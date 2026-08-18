# AASTeX v7 Paper Template

Local-first LaTeX project template for AAS-journal manuscripts on macOS, built
around VS Code and Zotero 8. It compiles with `latexmk` and `pdflatex` against a
vendored AASTeX v7 class, and generates its bibliography from a Better BibTeX
export enriched with NASA ADS records.

---

## Requirements

- macOS 10.15 or later
- MacTeX (`mactex-no-gui`), which provides `pdflatex`, `latexmk`, `bibtex`,
  `chktex` and `latexindent`
- VS Code with LaTeX Workshop (`james-yu.latex-workshop`)
- Zotero 8 with Better BibTeX 9.0.21 or newer
- `uv`, which resolves `bibtexparser~=1.4` and Python 3.11 or newer from the
  PEP 723 header in `tools/ads_enrich.py`
- Optional: an ADS API token in `ADS_DEV_KEY`. Without one, `make bib` degrades
  to `--offline`.

## Install

Install the toolchain and configure Zotero once per machine before the first
build. The project itself has no install step: the AASTeX class and the BibTeX
style are vendored, and `tools/ads_enrich.py` resolves its dependencies at run
time.

## Quick start

```bash
# from the project root
make                # build ms.pdf (regenerates references.bib if stale)
open build/ms.pdf

make bib            # refresh references.bib from Zotero + ADS
make bib-offline    # same, from cache alone: no token, no network
make watch          # continuous preview
make check-macros   # list every journal macro the class defines
make clean          # remove aux files, keep the PDF

make auto-on        # let any build refresh the bibliography by itself
make auto-status
make auto-off       # back to explicit `make bib` (the default)
```

One-time machine and GUI setup lives in [SETUP.md](SETUP.md).

In VS Code, `Cmd+Opt+B` builds and `Cmd+Opt+V` opens the PDF in a tab.
Build-on-save is configured. Before switching to `make watch`, set
`latex-workshop.latex.autoBuild.run` to `"never"` in
[.vscode/settings.json](.vscode/settings.json), or both drivers compile the same
file.

---

## Layout

```text
.
|-- ms.tex                  # main manuscript
|-- Makefile                # build, bibliography, macro check
|-- LICENSE                 # 0BSD, plus terms for the vendored AAS files
|-- aastex702.cls           # vendored AASTeX v7.0.2 class (June 2026 release)
|-- aasjournalv7.1.bst      # vendored AAS BibTeX style
|-- orcid-ID.png            # ORCID icon rendered next to \author names
|-- references.zotero.bib   # Better BibTeX auto-export target -- SOURCE
|-- references.bib          # GENERATED from the above -- what ms.tex reads
|-- tools/
|   `-- ads_enrich.py       # references.zotero.bib -> references.bib, via ADS
|-- figures/                # publication-resolution figures (committed)
|   `-- full/               # full-res originals (gitignored)
|-- sections/               # optional \input targets
|-- .latexmkrc              # build driver config, Overleaf-compatible
|-- cspell.json             # project spell-check dictionary
|-- .vscode/                # LaTeX Workshop, ChkTeX, LTeX+, recommended extensions
`-- build/                  # all aux output, gitignored
```

## Starting a new paper from this template

1. Click "Use this template" on GitHub, copy the directory, or `git clone` and
   then run `rm -rf .git && git init`.
2. Replace the placeholder front matter in [ms.tex](ms.tex): `\title`,
   `\author`/`\affiliation`/`\email`, `\shorttitle`, `\shortauthors`,
   `\keywords`. Every author needs an `\email` or the compile hard-errors.
3. Delete the example body sections and the `\todo` placeholders.
4. Point the Better BibTeX auto-export at `references.zotero.bib`
   ([SETUP.md](SETUP.md) section 3.5). The example entries are placeholders and
   will be overwritten.
5. Add instrument, survey, and software names to `cspell.json`, and to
   `ltex.dictionary` in `.vscode/settings.json`.

---

## House rules

- One sentence per line in `ms.tex`, with no hard-wrapping mid-sentence, so git
  diffs show which sentence changed. `Opt+Q` reflows a paragraph. The Markdown
  docs are wrapped at 80 columns instead.
- No `latex-workshop.latex.autoClean.run`; the `.aux` and `.bbl` files in `build/`
  keep incremental builds at about 0.1 s.
- BibTeX and natbib with `aasjournalv7.1.bst`, which biblatex and biber cannot
  drive. On the Zotero side that means Better BibTeX, not Better BibLaTeX, which
  emits `date` where BibTeX wants `year`.
- Edit neither `.bib` file by hand. Better BibTeX writes `references.zotero.bib`,
  `tools/ads_enrich.py` generates `references.bib` from it, and both are
  committed.
- `references.bib` does not refresh on its own. Add a paper in Zotero, cite it,
  and the build renders `??` until `make bib` runs. `make auto-on` closes the gap
  on every build for one `uv run` (about 200-400 ms) per changed export, except
  under `make watch`, which reads `.latexmkrc` once at startup.
- An `\email` for every `\author`. AASTeX 7.0.2 hard-errors without one and stops
  the compile before BibTeX runs, so the symptom is unresolved `??` citations.
- `pdflatex` only, not lualatex or xelatex.
- No `-outdir` in `.latexmkrc`; Overleaf breaks on a redirected output directory,
  so the `build/` redirect lives in the VS Code tool arguments and in the
  `-outdir` flag.
- Relative paths, forward slashes, ASCII filenames, and no `-shell-escape`
  dependency in anything shared.

---

## Cheatsheet

| Action | Shortcut |
|---|---|
| Build | `Cmd+Opt+B` |
| View PDF | `Cmd+Opt+V` |
| Forward search (source to PDF) | `Cmd+Opt+J` |
| Reverse search (PDF to source) | `Cmd+Click` in the PDF pane |
| Show compile log | `Cmd+Opt+L` |
| Reflow paragraph | `Opt+Q` |
| Cite from Zotero | `Opt+Shift+Z` |

Useful one-offs:

```bash
latexmk -c                              # remove aux files, keep the PDF
latexmk -C                              # remove aux files and the PDF
chktex -wall -n22 -n30 -n8 -e16 -q ms.tex
latexpand ms.tex > ms_flat.tex          # flatten \input before submission

export ADS_DEV_KEY=...                  # https://ui.adsabs.harvard.edu/user/settings/token
uv run tools/ads_enrich.py --in references.zotero.bib --out references.bib
uv run tools/ads_enrich.py --in references.zotero.bib --out references.bib --offline
uv run tools/ads_enrich.py --refresh    # ignore cached lookups, re-query ADS
uv run tools/ads_enrich.py --if-changed # no-op unless the export really changed
```

`ads_enrich.py` prints every entry it could not resolve to stderr. Software,
Zenodo DOIs and theses legitimately pass through unenriched, but a journal
article in that list means a bad DOI.

---

## Versions pinned here

| File | Version | Source |
|---|---|---|
| `aastex702.cls` | 7.0.2 (June 2026) | [AAS AASTeX page](https://journals.aas.org/aastex-package-for-manuscript-preparation/) |
| `aasjournalv7.1.bst` | v7.1 (June 2026) | same |

Both files are vendored rather than taken from TeX Live, whose `aastex` package
lags the AAS release and currently ships `aastex631.cls`. To update, download the
current files from the AAS page and replace both in one commit.

---

## License

The manuscript skeleton, build configuration, tooling and documentation are
[0BSD](LICENSE): use them for anything, with no attribution required.

Three files vendored from the AASTeX distribution are not covered by that
license: `aastex702.cls` (AAS, LPPL 1.3c), `aasjournalv7.1.bst` (Patrick W.
Daly, non-commercial use only) and `orcid-ID.png` (ORCID's mark).
[LICENSE](LICENSE) reproduces their terms in full. The `.bst` restriction is the
one that matters for commercial use of a copy of this repository.
