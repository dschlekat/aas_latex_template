# AASTeX manuscript build.
#
# references.bib is GENERATED from references.zotero.bib (the Better BibTeX
# auto-export target). Edit neither by hand: both get overwritten.

MAIN    := ms
OUTDIR  := build
LATEXMK := latexmk -pdf -outdir=$(OUTDIR)

.PHONY: all watch bib clean distclean check-macros auto-on auto-off auto-status

all: $(OUTDIR)/$(MAIN).pdf

$(OUTDIR)/$(MAIN).pdf: $(MAIN).tex references.bib
	$(LATEXMK) $(MAIN).tex

references.bib: references.zotero.bib tools/ads_enrich.py
	uv run tools/ads_enrich.py --in $< --out $@

# Rebuild the bibliography from cache alone -- no ADS token, no network.
.PHONY: bib-offline
bib-offline:
	uv run tools/ads_enrich.py --in references.zotero.bib --out references.bib --offline

bib: references.bib

# Auto-mode is the presence of .ads-auto (gitignored), which .latexmkrc checks,
# so the editor, the terminal and make all agree without an env var.
auto-on:
	@touch .ads-auto
	@echo "auto-enrichment ON: builds regenerate references.bib when Zotero exports."

auto-off:
	@rm -f .ads-auto
	@echo "auto-enrichment OFF: run 'make bib' after adding papers."

auto-status:
	@test -e .ads-auto \
	  && echo "auto-enrichment is ON  (.ads-auto present)" \
	  || echo "auto-enrichment is OFF (.ads-auto absent; run 'make auto-on')"

# Deliberately does NOT watch references.zotero.bib: BBT rewrites it on every
# library change, and an ADS query firing mid-compile is not what you want.
watch: references.bib
	latexmk -pvc -pdf -outdir=$(OUTDIR) $(MAIN).tex

# The class writes `\newcommand\apj{...}` with no braces around the name, so
# the obvious grep for '\newcommand{\...}' finds nothing.
check-macros:
	@grep -oE '\\newcommand\\[a-zA-Z]+\{\\ref@jnl\{[^}]*\}\}' aastex702.cls \
	  | sed -E 's/.*\\newcommand\\([a-zA-Z]+)\{\\ref@jnl\{(.*)\}\}/\1\t\2/' | sort

clean:
	$(LATEXMK) -c $(MAIN).tex

distclean:
	$(LATEXMK) -C $(MAIN).tex
	rm -rf $(OUTDIR)
