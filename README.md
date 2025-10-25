# ValmikiRamayanam

Valmiki Ramayanam PDFs generated from TeX.

## Generating TeX files

The repository contains a helper script that converts the JSON sources in
`src/data` into TeX files.  The script searches the data directory recursively
and mirrors the LaTeX folder structure (`TeX/1-BalaKanda`,
`TeX/2-AyodhyaKanda`, …).  Each shloka is rendered with the matching macro –
`\onelineshloka`, `\twolineshloka`, or `\threelineshloka` – and the closing
line is annotated with the corresponding Kanda/Sarga/Shloka number comment.

```bash
python scripts/generate_tex.py --verbose
```

The script accepts a few useful flags:

* `--data-dir`: location of the JSON source files (defaults to `src/data`).
* `--output-dir`: directory where the TeX files are written (defaults to `TeX`).
* `--map-file`: path to `ramayana_map.json` that stores chapter titles.
* `--overwrite`: regenerate TeX files even if they already exist.

The map file is optional; when present the generated TeX file starts with a
`\chapter{…}` heading populated with the chapter title.
