# One-time setup

Machine-level and GUI steps that live outside the repo. Do these once per
machine.

---

## 1. Toolchain

```bash
# Homebrew, if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Full TeX Live without the BasicTeX GUI apps (~5.5 GB download)
brew install --cask mactex-no-gui

# MacTeX ships a frozen snapshot; bring it current
sudo tlmgr update --self --all

# Optional
brew install --cask tex-live-utility   # GUI for tlmgr
brew install --cask skim               # external PDF viewer, best-in-class SyncTeX
brew install ghostscript qpdf          # figure/PDF manipulation
```

Binaries land in `/Library/TeX/texbin`, registered via `/etc/paths.d/TeX`.
Verify:

```bash
which pdflatex latexmk bibtex chktex latexindent
pdflatex --version
```

`kpsewhich aastex702.cls` returning nothing is fine, the class is vendored in
this repo rather than taken from TeX Live.

The full install exists to eliminate `tlmgr install` interruptions mid-deadline.
If 5.5 GB is unacceptable, `brew install --cask basictex` then
`sudo tlmgr install collection-latexextra collection-fontsrecommended collection-bibtexextra latexmk latexindent chktex aastex`,
and budget an hour of iterative "missing package" cycles.

---

## 2. VS Code extensions

Open this folder in VS Code and accept the workspace recommendation prompt, or
install by hand:

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

Notes:

- `dnut.rewrap-revived` replaces the original `stkb.rewrap`, which now fails
  VS Code's extension signature check (`NotSigned`).
- `efoerster.texlab` is a lighter LSP-only alternative to LaTeX Workshop, but
  you lose the integrated viewer and recipe system. **Do not install both** —
  they conflict.
- Install `ltex-plus.vscode-ltex-plus`, not the abandoned `valentjn.vscode-ltex`.

### Configure the Zotero picker

`mblode.zotero` ships its own bindings: `Opt+Shift+Z` opens the citation picker,
`Ctrl+Shift+Z` opens the selected item in Zotero, `Ctrl+Opt+Shift+Z` opens its
PDF. The picker is also on the Command Palette as **Zotero Citation Picker**.
Rebind via `Cmd+K Cmd+S` if you want something else.

The setting that matters is the output format, and this repo already sets it in
[.vscode/settings.json](.vscode/settings.json):

```json
"zotero-citation-picker.port": "http://127.0.0.1:23119/better-bibtex/cayw?format=citep"
```

Left alone the extension defaults to Pandoc and inserts `[@key]` into your
`.tex` file, which is not what you want. `format=citep` and `format=citet` are
aliases for `format=natbib` with the respective command; plain
`format=natbib&command=<cmd>` covers anything else. Append `&minimize=true` if
you would rather Zotero not steal focus on every pick.

LaTeX Workshop binds everything else: `Cmd+Opt+B` build, `Cmd+Opt+V` view,
`Cmd+Opt+J` forward search, `Cmd+Opt+L` log, `Cmd+Click` in the PDF pane for
reverse search.

---

## 3. Zotero → BibTeX pipeline

### 3.1 Install Better BibTeX

**Zotero 8 and Better BibTeX 9.0.21 or newer.** BBT 9 requires Zotero 8, which
in turn wants macOS 10.15 or later.

Zotero → Tools → Plugins → gear icon → **Install Plugin From File** → select the
`.xpi` from
[retorquere.github.io/zotero-better-bibtex](https://retorquere.github.io/zotero-better-bibtex/).
Restart Zotero afterwards.

Citation keys live in Zotero's own Citation Key field, which syncs like any
other field. Your keys therefore travel between machines rather than sitting in
a local plugin database, and BBT reads and writes them there.

### 3.2 Getting astronomy metadata in: use the connector

On an ADS **abstract** page the dedicated NASA ADS translator captures good
metadata and writes an `ADS Bibcode:` line into the item's Extra field, which is
what everything below hangs off of.

- **The ADS translator breaks periodically** after ADS front-end changes. The
  connector then silently falls back to the generic Embedded Metadata
  translator, which still produces a usable item but drops the bibcode. An item
  with no `ADS Bibcode:` in Extra means this happened — re-save it.
- **Bulk saves from search-result pages** have historically attached PDFs to the
  wrong records. For batches, use the identifier route instead.

**Add Item by Identifier** is the fast bulk route: Zotero's magic-wand button
accepts ADS bibcodes directly. On an ADS results page, select records → Export →
**Bibcodes**, then paste the whole list into the identifier box. No connector,
no per-item clicking, metadata straight from ADS.

**No plugin will fix an item after the fact.** Guides still recommend
[`zot-nasa-ads`](https://github.com/samuelyeewl/zot-nasa-ads) for pulling ADS
metadata onto an item you already saved; it caps out at
`strict_max_version: "7.0.*"`, so Zotero refuses to install it. Do not go
looking for it.

So an item whose Extra is missing `ADS Bibcode:` gets fixed by hand: paste the
line in yourself, or delete the item and re-save it from the ADS abstract page,
then refresh the key (§3.3). Promoting a preprint to its published version is
likewise a re-save.

Only the *citation key* depends on that bibcode. The bibliography itself does
not: `ads_enrich.py` resolves entries through the DOI and the arXiv eprint as
well as the bibcode, and takes ADS's published record wholesale (§3.6).

### 3.3 Citation keys: set the formula, then leave it alone

Keys must be **stable**. A key that regenerates when you edit metadata silently
breaks every `\citep{}` that used it.

**Every key is pinned.** Zotero has nowhere to record whether a key was pinned
deliberately, so BBT treats all of them as fixed once written. Two consequences
worth knowing before you read any tutorial on this: writing `Citation Key: X`
into an item's Extra field does nothing, and neither does the `$pinned()`
formatter that older key formulas are built around.

> Pinned citation keys in Extra are no longer supported, but existing formulas
> may still reference `$pinned()`. Keep this formatter as a no-op.

Three settings under Zotero → Settings → Better BibTeX → **Citation keys**:

| Setting | Value |
|---|---|
| Citation key formula | `extra('ADS Bibcode') \| auth.lower + year + shorttitle(1,0)` |
| Regenerate citation key when item changes | **off** |
| Automatically fill citation key after | a few seconds |

The formula reads the `ADS Bibcode:` line the connector wrote (§3.2), giving the
astro-conventional bibcode key. Items with no bibcode — arXiv-only preprints,
software, technotes — fall through to the collision-resistant generated form.
Turning off regeneration is the setting that actually protects your citations.

The separator between alternatives is `|` or `;`; the settings pane validates as
you type. If `extra('ADS Bibcode')` comes back empty for an item you know has a
bibcode, check that Extra really contains a line of the form
`ADS Bibcode: 2024ApJ...961..112S`. BBT's own docs only advertise `extra()` for
`tex.*` fields and a fixed list of CSL names, but the implementation falls back
to scanning raw Extra lines for `Label: value`, which is why an ad-hoc label
like `ADS Bibcode` resolves.

Existing items keep whatever key they already have: select them → right-click →
Better BibTeX → **Refresh** to apply the new formula.

#### The formula gets exactly one shot per item

Keys are pinned and auto-fill is on, so the formula runs *once*, about two
seconds after an item appears, and whatever it produces is written to the
Citation Key field and kept.

That is a race against the bibcode. If Extra has no `ADS Bibcode:` line at the
instant auto-fill runs, because the ADS translator silently fell back to
Embedded Metadata (§3.2) or because you pasted the bibcode in afterwards, the
item keeps the `auth.lower + year` fallback key permanently. Nothing revisits it
on its own, and no plugin will repair it for you (§3.2).

So after adding papers, sort by Date Added and check the keys. Anything that
should be a bibcode and is not: fix Extra, then right-click → Better BibTeX →
**Refresh**. Do this *before* you cite the item: Refresh changes the key, and a
key that changes after it is in `ms.tex` is exactly the silent `\citep{}` break
this section exists to prevent.

Right-click the column headers in the items list and enable **Citation key** to
make this a glance rather than a per-item click. BBT also keeps the key at the
top of the item pane for whatever item is selected.

### 3.4 Export settings

Zotero → Settings → Better BibTeX → Export:

- **Fields to omit:** `abstract, file, keywords, note` — keeps the `.bib`
  readable and diffable.
- **Enable** "Export unicode as plain-text LaTeX commands" — turns `Müller` into
  `M\"uller`, which BibTeX's older `.bst` machinery handles reliably.
- **Automatic export: On change**, not "on idle", so the `.bib` is current the
  moment you add a paper.
- **Journal abbreviation mode:** leave it on the default, *always use the Zotero
  abbreviation field*. There is no "off" setting; the other two modes reach for
  Zotero's auto-abbreviation, which produces `Astrophys. J.` and collides with
  the journal macros `ads_enrich.py` installs (§3.6).

Use **Better BibTeX**, not Better BibLaTeX: the BibLaTeX exporter emits `date`
where BibTeX wants `year`, and `aasjournalv7.1.bst` will not read it.

BibTeX lowercases title words unless braced. To protect an acronym like *HDPS*,
wrap it in the Zotero title field as `<span class="nocase">HDPS</span>`; BBT
converts it to `{HDPS}` on export.

### 3.5 Live auto-export to this project

1. Create a Zotero collection for the paper.
2. Right-click the collection → **Export Collection**.
3. Format: **Better BibTeX**. Check **Keep updated**.
4. Save as **`references.zotero.bib`** in this project root.

Note the filename. `references.zotero.bib` is the *source*; `references.bib` is
generated from it. Getting this backwards means BBT and `ads_enrich.py` fight
over the same file.

```text
Zotero collection
   └─(BBT auto-export, keep updated)→ references.zotero.bib   [committed, never edited]
        └─(make bib)→ references.bib                          [committed, GENERATED]
                          └→ \bibliography{references}
```

### 3.6 Journal macros and enrichment: `make bib`

`aasjournalv7.1.bst` renders AAS-style abbreviations when the `journal` field
holds a macro like `\apj`, but the Zotero connector writes the full journal
name. [tools/ads_enrich.py](tools/ads_enrich.py) fixes that and rather more: it
takes ADS's own record wholesale, so you also get `eprint`/`archivePrefix`,
`adsurl`, canonical page ranges and author lists, and published-version DOIs for
entries you saved as preprints. It keeps your citation key, so every `\citep{}`
keeps working.

```bash
export ADS_DEV_KEY=...   # https://ui.adsabs.harvard.edu/user/settings/token
make bib                 # or: make bib-offline, from cache alone
```

Put the export line in `~/.zshrc`. Without a key it degrades to `--offline` and
passes entries through unchanged rather than failing, so the build always works.

**Automatic mode.** By default you run `make bib` yourself. To have any build
regenerate the bibliography when Zotero has exported:

```bash
make auto-on       # builds now regenerate references.bib as needed
make auto-status
make auto-off
```

This flips a gitignored `.ads-auto` file that `.latexmkrc` checks, so it applies
equally to `Cmd+Opt+B`, build-on-save, bare `latexmk`, and `make` — and stays
inert on Overleaf, which has neither the flag file nor `uv`. One gap: `make
watch` reads `.latexmkrc` once at startup, so a long-running watch session will
not notice papers added mid-session.

**Undefined macros are a hard compile error.** ADS emits macros from a wider set
than AASTeX defines — `\ascom`, `\aph` and `\rsi` are all real ADS output and
none are defined by `aastex702.cls`. `ads_enrich.py` checks every macro against
the vendored class and falls back to the full journal name, so enriched entries
cannot break the build. Entries ADS cannot resolve pass through untouched; if
one of those carries an unknown macro you get a warning naming the entry. To see
what the class defines: `make check-macros`.

### 3.7 Cite-as-you-write

With Zotero running, `mblode.zotero` queries Better BibTeX's CAYW endpoint on
`127.0.0.1:23119` and inserts `\citep{key}` from a search dialog: `Opt+Shift+Z`,
or Command Palette → **Zotero Citation Picker**. The `format=citep` in section 2
is what makes it emit `\citep{}` rather than Pandoc brackets.

CAYW is a Better BibTeX feature, not a Zotero one, so it needs both BBT loaded
and Zotero running. To check the endpoint without popping the picker:

```bash
curl 'http://127.0.0.1:23119/better-bibtex/cayw?probe=1'   # answers: ready
```

A picker that hangs or returns nothing on a BBT older than 9.0.21 is that
version, not your configuration (§3.1).

If the picker fails, LaTeX Workshop's own `\citep{` IntelliSense is the fallback
and needs nothing running.

---

## 4. Verify

```bash
make bib-offline                    # regenerate references.bib from cache
latexmk -pdf -outdir=build ms.tex   # expect resolved citations, no ?? markers
grep -c "Warning" build/ms.log      # should be small; inspect anything unexpected
```

Checklist:

- [ ] PDF renders in the VS Code tab
- [ ] `Cmd+Opt+J` jumps the PDF to your cursor position
- [ ] `Cmd+Click` in the PDF jumps back to source
- [ ] Typing `\citep{` offers completions from `references.bib`
- [ ] Adding a paper in Zotero updates `references.zotero.bib` within a few seconds
- [ ] A paper saved from an ADS abstract page gets a *bibcode* citation key, not
      an `auth+year` one (§3.3)
- [ ] `make bib` then carries it into `references.bib` with an ADS-quality record
- [ ] `Opt+Shift+Z` opens the Zotero picker and inserts a `\citep{}`, not `[@key]`
- [ ] Citations render author-year, and the reference list uses journal abbreviations

If citations come out as `??` and the log has no obvious BibTeX error, check
that every `\author` has an `\email`. AASTeX 7.0.2 hard-errors on a missing one
and stops the compile before BibTeX runs, so the visible symptom is unresolved
citations rather than a missing-email message.
