# Overleaf reads this file, so keep it portable.
#
# Do NOT set $out_dir: Overleaf breaks on a redirected output directory. The
# build/ redirect lives in .vscode/settings.json and in the -outdir flag.

$pdf_mode = 1;
$pdflatex = 'pdflatex -synctex=1 -interaction=nonstopmode -file-line-error -halt-on-error=0 %O %S';

# 2 = run bibtex, and treat the .bbl as a regenerable intermediate file.
$bibtex_use = 2;

$max_repeat = 5;

@default_files = ('ms.tex');

# Extensions removed by `latexmk -c` on top of the built-in list.
$clean_ext = 'synctex.gz bbl fdb_latexmk fls spl';

# Auto-enrichment of the bibliography, toggled by `make auto-on`. Runs at
# rc-load time, before latexmk computes any dependency state, so the fresh
# references.bib is in place before BibTeX reads it. Inert on Overleaf, which
# has neither the gitignored .ads-auto nor `uv`.
#
# `latexmk -pvc` reads this file once at startup, so a watch session will not
# pick up papers added mid-session -- restart it, or run `make bib`.
if (-e '.ads-auto' && -e 'references.zotero.bib' && -e 'tools/ads_enrich.py') {
    # Cheap mtime gate: when Zotero has not exported, spawn nothing at all.
    my $src_time = (stat 'references.zotero.bib')[9];
    my $out_time = (-e 'references.bib') ? (stat 'references.bib')[9] : 0;
    if ($src_time > $out_time) {
        # --if-changed no-ops when BBT rewrote the export byte-identically,
        # which it does on any library change.
        my $rc = system('uv', 'run', 'tools/ads_enrich.py',
                        '--in',  'references.zotero.bib',
                        '--out', 'references.bib',
                        '--if-changed');
        # A stale bibliography beats no PDF.
        warn "ads_enrich failed (status $rc); "
           . "building with the existing references.bib\n" if $rc != 0;
    }
}
