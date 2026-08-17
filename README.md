# AASTeX v7 Paper Template

Local-first LaTeX project template for AAS-journal manuscripts: macOS + VS Code + Zotero, compiling with `latexmk`/`pdflatex` against a vendored AASTeX v7 class.

One-time machine and GUI setup lives in [SETUP.md](SETUP.md).

---

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

In VS Code, `Cmd+Opt+B` builds and `Cmd+Opt+V` opens the PDF in a tab. Building
on save is already configured — if you switch to `make watch`, set
`latex-workshop.latex.autoBuild.run` to `"never"` in
[.vscode/settings.json](.vscode/settings.json) or you get duplicated compiles.

---

## Layout

```text
.
├── ms.tex                  # main manuscript
├── Makefile                # build, bibliography, macro check
├── LICENSE                 # 0BSD, plus terms for the vendored AAS files
├── aastex702.cls           # vendored AASTeX v7.0.2 class (June 2026 release)
├── aasjournalv7.1.bst      # vendored AAS BibTeX style
├── orcid-ID.png            # ORCID icon rendered next to \author names
├── references.zotero.bib   # Better BibTeX auto-export target -- SOURCE
├── references.bib          # GENERATED from the above -- what ms.tex reads
├── tools/
│   └── ads_enrich.py       # references.zotero.bib -> references.bib, via ADS
├── figures/                # publication-resolution figures (committed)
│   └── full/               # full-res originals (gitignored)
├── sections/               # optional \input targets
├── .latexmkrc              # build driver config, Overleaf-compatible
├── cspell.json             # project spell-check dictionary
├── .vscode/                # LaTeX Workshop, ChkTeX, LTeX+, recommended extensions
└── build/                  # all aux output, gitignored
```

## Starting a new paper from this template

1. Click **Use this template** on GitHub (or copy the directory, or `git clone`
   and `rm -rf .git && git init`).
2. Replace the placeholder front matter in [ms.tex](ms.tex): `\title`,
   `\author`/`\affiliation`/`\email`, `\shorttitle`, `\shortauthors`,
   `\keywords`. Every author needs an `\email` or the compile hard-errors.
3. Delete the example body sections and the `\todo` placeholders.
4. Point the Better BibTeX auto-export at `references.zotero.bib`
   ([SETUP.md](SETUP.md) section 3). The example entries are placeholders and
   will be overwritten.
5. Add instrument, survey, and software names to `cspell.json`, and to
   `ltex.dictionary` in `.vscode/settings.json`.

---

## House rules

**One sentence per line.** No hard-wrapping mid-sentence. Git diffs then show
which sentence changed rather than a reflowed paragraph, which is what makes
reconciling browser-side Overleaf edits tractable. `Opt+Q` reflows a paragraph
when you do need it.

**Never auto-clean.** `latex-workshop.latex.autoClean.run` is `"never"` on
purpose: the `.aux`/`.bbl` in `build/` are what make incremental builds instant.

**BibTeX, not biblatex.** AASTeX v7 mandates BibTeX + natbib +
`aasjournalv7.1.bst`, which biblatex/biber cannot drive. On the Zotero side that
means the **Better BibTeX** exporter, not Better BibLaTeX — BibLaTeX emits
`date` where BibTeX wants `year`.

**Two `.bib` files, one direction of flow.** Better BibTeX writes
`references.zotero.bib`; `tools/ads_enrich.py` generates `references.bib` from
it. Edit neither by hand. Commit both: they are build inputs and the journal
needs them.

```text
Zotero  ──BBT auto-export──▶  references.zotero.bib  ──make bib──▶  references.bib
```

**`references.bib` does not refresh on its own by default.** Add a paper in
Zotero, cite it, build, and you get `??` until you run `make bib` — the Zotero
half of the chain is automatic, the enrichment half is not. `make auto-on` makes
every build close the gap, at the cost of a `uv run` (~200-400 ms) on the builds
where Zotero actually exported something. Builds where nothing changed spawn no
process at all.

Auto-mode is a gitignored `.ads-auto` file that `.latexmkrc` checks, so the
editor, the terminal and make all agree, and it stays inert on Overleaf. One
gap: `make watch` reads `.latexmkrc` once at startup and misses papers added
mid-session.

**Every `\author` needs an `\email`.** AASTeX 7.0.2 hard-errors without one and
stops the compile *before* BibTeX runs, so the symptom is unresolved `??`
citations rather than a message about email.

**pdflatex, not lualatex/xelatex.** AAS production does not want the others.

**Keep `-outdir` out of `.latexmkrc`.** Overleaf reads `latexmkrc` but breaks on
a redirected output directory, so the `build/` redirect lives in the VS Code
tool args and in the `-outdir` flag you type.

**Portability.** Relative paths, forward slashes, ASCII filenames, no
`-shell-escape` dependencies in anything shared.

---

## Speed knobs

You will probably never need these. In order of payoff:

1. **Draft-mode figures.** Set `\draftfigstrue` in the `ms.tex` preamble and
   `\includegraphics` emits a labeled box instead of rasterizing. Large win with
   many multi-MB PNGs. Flip it back before generating a final PDF.
2. **Downsample draft figures.** Keep originals in `figures/full/`:

   ```bash
   sips -Z 1200 figures/full/*.png --out figures/
   ```

3. **Externalize TikZ** if you have non-trivial TikZ: `\usetikzlibrary{external}`
   + `\tikzexternalize`. Needs `-shell-escape`, so commit the cached PDFs rather
   than pushing the build step.
4. **Precompiled preamble** (`mylatexformat`). Marginal at AASTeX scale and a
   fragile extra build step. Skip it.

---

## Cheatsheet

| Action | Shortcut |
|---|---|
| Build | `Cmd+Opt+B` |
| View PDF | `Cmd+Opt+V` |
| Forward search (source → PDF) | `Cmd+Opt+J` |
| Reverse search (PDF → source) | `Cmd+Click` in the PDF pane |
| Show compile log | `Cmd+Opt+L` |
| Reflow paragraph | `Opt+Q` |
| Cite from Zotero | `Cmd+Shift+Z` (bind manually, see SETUP.md) |

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

Vendored deliberately rather than taken from TeX Live, whose `aastex` package
lags the AAS release (it currently ships `aastex631.cls`). Pinning means your
local PDF matches what coauthors and the journal see. To update, re-download
`aastex702.zip` from the AAS page and replace both files in one commit.

---

## License

Everything in this repository that is mine — the manuscript skeleton, build
configuration, tooling and docs — is [0BSD](LICENSE): do whatever you like with
it, no attribution required.

Three files are vendored from the AASTeX distribution and are **not** covered by
that: `aastex702.cls` (AAS, LPPL 1.3c), `aasjournalv7.1.bst` (Patrick W. Daly,
non-commercial use only) and `orcid-ID.png` (ORCID's mark). [LICENSE](LICENSE)
reproduces their terms in full. The `.bst` restriction is the one to notice if
you are doing anything commercial with a copy of this repo.
