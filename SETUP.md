# One-time setup

Machine-level and GUI steps that live outside the repository. Do these once per
machine.

---

## 1. Toolchain

Install Homebrew if it is not already present.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install full TeX Live without the BasicTeX GUI applications. The download is
about 5.5 GB.

```bash
brew install --cask mactex-no-gui
```

Bring the frozen snapshot MacTeX ships current.

```bash
sudo tlmgr update --self --all
```

Install `uv`, which runs `tools/ads_enrich.py` and resolves `bibtexparser~=1.4`
and Python 3.11 or newer from that script's PEP 723 header.

```bash
brew install uv
```

Install the optional tools.

```bash
brew install --cask tex-live-utility   # GUI for tlmgr
brew install --cask skim               # external PDF viewer, best-in-class SyncTeX
brew install ghostscript qpdf          # figure/PDF manipulation
```

Verify the TeX binaries. They land in `/Library/TeX/texbin`, registered via
`/etc/paths.d/TeX`.

```bash
which pdflatex latexmk bibtex chktex latexindent
pdflatex --version
```

`kpsewhich aastex702.cls` returning nothing is expected, since the class is
vendored in this repository rather than taken from TeX Live.

Where 5.5 GB is unacceptable, install BasicTeX and add the packages by hand
instead, at the cost of iterative missing-package cycles later.

```bash
brew install --cask basictex
sudo tlmgr install collection-latexextra collection-fontsrecommended collection-bibtexextra latexmk latexindent chktex aastex
```

---

## 2. VS Code extensions

Open this folder in VS Code and accept the workspace recommendation prompt, or
install the extensions by hand.

```bash
code --install-extension james-yu.latex-workshop          # essential
code --install-extension mblode.zotero                    # cite-as-you-write
code --install-extension ltex-plus.vscode-ltex-plus       # LaTeX-aware grammar
code --install-extension streetsidesoftware.code-spell-checker
code --install-extension dnut.rewrap-revived              # Opt+Q paragraph reflow

# optional
code --install-extension tecosaur.latex-utilities         # live word count
code --install-extension eamodio.gitlens
```

Three constraints on that list:

- Install `dnut.rewrap-revived`, not `stkb.rewrap`, which fails VS Code's
  extension signature check (`NotSigned`).
- Install `ltex-plus.vscode-ltex-plus`, not the abandoned `valentjn.vscode-ltex`.
- `efoerster.texlab` is a lighter LSP-only alternative to LaTeX Workshop, at the
  cost of the integrated viewer and the recipe system. Do not install both, as
  they conflict.

### Configure the Zotero picker

`mblode.zotero` ships its own bindings: `Opt+Shift+Z` opens the citation picker,
`Ctrl+Shift+Z` opens the selected item in Zotero, and `Ctrl+Opt+Shift+Z` opens
its PDF. The picker is also on the Command Palette as Zotero Citation Picker.
Rebind through `Cmd+K Cmd+S`.

The setting that matters is the output format, which this repository already sets
in [.vscode/settings.json](.vscode/settings.json):

```json
"zotero-citation-picker.port": "http://127.0.0.1:23119/better-bibtex/cayw?format=citep"
```

`format=citep` and `format=citet` are aliases for `format=natbib` with the
respective command, and plain `format=natbib&command=<cmd>` covers anything else.
Append `&minimize=true` to keep Zotero from taking focus on every pick.

LaTeX Workshop binds everything else: `Cmd+Opt+B` build, `Cmd+Opt+V` view,
`Cmd+Opt+J` forward search, `Cmd+Opt+L` log, and `Cmd+Click` in the PDF pane for
reverse search.

---

## 3. Zotero -> BibTeX pipeline

### 3.1 Install Better BibTeX

Better BibTeX 9.0.21 or newer is the baseline. BBT 9 requires Zotero 8, which in
turn requires macOS 10.15 or later.

Download the `.xpi` from
[retorquere.github.io/zotero-better-bibtex](https://retorquere.github.io/zotero-better-bibtex/),
then install it through Zotero -> Tools -> Plugins -> gear icon -> Install Plugin
From File. Restart Zotero afterwards.

Citation keys live in Zotero's own Citation Key field, so they sync between
machines like any other field.

### 3.2 Astronomy metadata through the connector

Save papers from an ADS abstract page. The dedicated NASA ADS translator captures
good metadata and writes an `ADS Bibcode:` line into the item's Extra field,
which is what everything below hangs off of.

Two failure modes:

- The ADS translator breaks periodically after ADS front-end changes. The
  connector then silently falls back to the generic Embedded Metadata translator,
  which still produces a usable item but drops the bibcode. An item with no
  `ADS Bibcode:` line in Extra means this happened, so re-save it.
- Bulk saves from search-result pages have attached PDFs to the wrong records.
  Use the identifier route for batches.

Use Add Item by Identifier as the fast bulk route. Zotero's magic-wand button
accepts ADS bibcodes directly. On an ADS results page, select the records, choose
Export -> Bibcodes, then paste the whole list into the identifier box. That route
needs no connector and no per-item clicking, and takes metadata straight from ADS.

No plugin repairs an item after the fact.
[`zot-nasa-ads`](https://github.com/samuelyeewl/zot-nasa-ads), which guides still
recommend for pulling ADS metadata onto a saved item, caps out at
`strict_max_version: "7.0.*"` and will not install.

Fix a missing `ADS Bibcode:` line by pasting it into Extra, or by deleting the
item and re-saving it from the ADS abstract page, then refresh the key
(section 3.3). Promoting a preprint to its published version is likewise a
re-save.

Only the citation key depends on that bibcode. `ads_enrich.py` resolves the
bibliography through the DOI and the arXiv eprint as well (section 3.6).

### 3.3 Citation key formula

Set three settings under Zotero -> Settings -> Better BibTeX -> Citation keys.

| Setting | Value |
|---|---|
| Citation key formula | `extra('ADS Bibcode') \| auth.lower + year + shorttitle(1,0)` |
| Regenerate citation key when item changes | off |
| Automatically fill citation key after | a few seconds |

The formula reads the `ADS Bibcode:` line the connector wrote (section 3.2),
giving the astro-conventional bibcode key. Items with no bibcode, such as
arXiv-only preprints and software, fall through to the collision-resistant
generated form. Regeneration stays off because a key that changes after it reaches
`ms.tex` breaks every `\citep{}` that used it.

Keys are pinned as soon as BBT writes them, so the formula runs once, about two
seconds after an item appears. Writing `Citation Key:` into an item's Extra field
does nothing, and the `$pinned()` formatter is a no-op. An item whose Extra had no
`ADS Bibcode:` line at that moment keeps the `auth.lower + year` fallback key
until it is refreshed by hand.

So sort by Date Added after adding papers and check the keys. To repair one, add a
line of the form `ADS Bibcode: 2024ApJ...961..112S` to Extra, then right-click ->
Better BibTeX -> Refresh. Refresh changes the key, so do it before citing the
item. The same Refresh applies a new formula to items that already have keys.

Right-click the column headers in the items list and enable Citation key to check
keys at a glance.

### 3.4 Export settings

Set these under Zotero -> Settings -> Better BibTeX -> Export.

- Fields to omit: `abstract, file, keywords, note`.
- Enable "Export unicode as plain-text LaTeX commands", which turns `Müller` into
  `M\"uller`.
- Automatic export: On change, not "on idle".
- Journal abbreviation mode: leave the default, always use the Zotero abbreviation
  field. The other two modes produce `Astrophys. J.` and collide with the journal
  macros `ads_enrich.py` installs (section 3.6).

Choose Better BibTeX, not Better BibLaTeX. The BibLaTeX exporter emits `date`
where BibTeX wants `year`, and `aasjournalv7.1.bst` will not read it.

BibTeX lowercases title words unless they are braced. To protect an acronym such
as HDPS, wrap it in the Zotero title field as `<span class="nocase">HDPS</span>`,
which BBT converts to `{HDPS}` on export.

### 3.5 Live auto-export to this project

1. Create a Zotero collection for the paper.
2. Right-click the collection and choose Export Collection.
3. Set the format to Better BibTeX and check Keep updated.
4. Save the file as `references.zotero.bib` in this project root.

`references.zotero.bib` is the source, and `references.bib` is generated from it.
Reversing the two makes BBT and `ads_enrich.py` fight over one file.

```text
Zotero collection
    |
    v  BBT auto-export, keep updated
references.zotero.bib      [committed, never edited]
    |
    v  make bib
references.bib             [committed, GENERATED]
    |
    v
\bibliography{references}
```

### 3.6 Journal macros and enrichment

`aasjournalv7.1.bst` renders AAS-style abbreviations when the `journal` field
holds a macro like `\apj`, but the Zotero connector writes the full journal name.
[tools/ads_enrich.py](tools/ads_enrich.py) fixes that by taking ADS's own record
wholesale, which also supplies `eprint` and `archivePrefix`, `adsurl`, canonical
page ranges and author lists, and published-version DOIs for entries saved as
preprints. It keeps the Zotero citation key, so every `\citep{}` keeps working.

Export an ADS token, then regenerate the bibliography.

```bash
export ADS_DEV_KEY=...   # https://ui.adsabs.harvard.edu/user/settings/token
make bib                 # or: make bib-offline, from cache alone
```

Put the export line in `~/.zshrc`. Without a key the script degrades to
`--offline` and passes entries through unchanged rather than failing, so the build
always works.

Automatic mode is off by default, leaving `make bib` as an explicit step. To have
any build regenerate the bibliography when Zotero has exported:

```bash
make auto-on       # builds now regenerate references.bib as needed
make auto-status
make auto-off
```

That flips a gitignored `.ads-auto` file which `.latexmkrc` checks, so it covers
`Cmd+Opt+B`, build-on-save, bare `latexmk` and `make`, and stays inert on
Overleaf. `make watch` is the exception, since it reads `.latexmkrc` once at
startup and will not notice papers added mid-session.

An undefined journal macro is a hard compile error, and ADS emits macros from a
wider set than `aastex702.cls` defines. `ads_enrich.py` checks every macro against
the vendored class and falls back to the full journal name, so enriched entries
cannot break the build. Entries ADS cannot resolve pass through untouched, and one
of those carrying an unknown macro produces a warning naming the entry. Run
`make check-macros` to list what the class defines.

### 3.7 Cite-as-you-write

With Zotero running, `mblode.zotero` queries Better BibTeX's CAYW endpoint on
`127.0.0.1:23119` and inserts `\citep{key}` from a search dialog. Open it with
`Opt+Shift+Z`, or through Command Palette -> Zotero Citation Picker. The
`format=citep` setting from section 2 is what makes it emit `\citep{}` rather
than Pandoc brackets.

CAYW is a Better BibTeX feature rather than a Zotero one, so it needs both BBT
loaded and Zotero running. Check the endpoint without opening the picker:

```bash
curl 'http://127.0.0.1:23119/better-bibtex/cayw?probe=1'   # answers: ready
```

LaTeX Workshop's own `\citep{` IntelliSense is the fallback if the picker fails,
and it needs nothing running.

---

## 4. Verify

Regenerate the bibliography and build.

```bash
make bib-offline                    # regenerate references.bib from cache
latexmk -pdf -outdir=build ms.tex   # expect resolved citations, no ?? markers
grep -c "Warning" build/ms.log      # should be small; inspect anything unexpected
```

Then confirm each item:

- [ ] PDF renders in the VS Code tab
- [ ] `Cmd+Opt+J` jumps the PDF to the cursor position
- [ ] `Cmd+Click` in the PDF jumps back to source
- [ ] Typing `\citep{` offers completions from `references.bib`
- [ ] Adding a paper in Zotero updates `references.zotero.bib` within a few
      seconds
- [ ] A paper saved from an ADS abstract page gets a bibcode citation key, not an
      `auth+year` one (section 3.3)
- [ ] `make bib` then carries it into `references.bib` with an ADS-quality record
- [ ] `Opt+Shift+Z` opens the Zotero picker and inserts a `\citep{}`, not
      `[@key]`
- [ ] Citations render author-year, and the reference list uses journal
      abbreviations

If citations come out as `??` and the log has no obvious BibTeX error, check that
every `\author` has an `\email`. AASTeX 7.0.2 hard-errors on a missing one and
stops the compile before BibTeX runs, so the visible symptom is unresolved
citations rather than a missing-email message.
