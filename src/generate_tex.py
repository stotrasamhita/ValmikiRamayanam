import json
import re
from pathlib import Path

# -------- Paths --------
DATA_DIR = Path("./data")
TEX_DIR = Path("../TeX")
MAP_PATH = Path("ramayana_map.json")

# -------- Load map (array of kandas) --------
with MAP_PATH.open(encoding="utf-8") as f:
    KANDA_LIST = json.load(f)  # <-- this is a LIST per your file

# Build a quick index: kanda_pos -> kanda_obj
KANDA_BY_POS = {k["pos"]: k for k in KANDA_LIST}

# English folder names + file prefixes (adjust if you prefer other spellings)
KANDA_EN = {
    1: ("BalaKanda", "bala-kanda"),
    2: ("AyodhyaKanda", "ayodhya-kanda"),
    3: ("AranyaKanda", "aranya-kanda"),
    4: ("KishkindaKanda", "kishkinda-kanda"),
    5: ("SundaraKanda", "sundara-kanda"),
    6: ("YuddhaKanda", "yuddha-kanda"),
    7: ("UttaraKanda", "uttara-kanda"),
}

# -------- Helpers --------

DEV_NUMS = "०१२३४५६७८९"
def to_devanagari(n: int) -> str:
    return "".join(DEV_NUMS[int(d)] for d in str(n))

# remove danda marks and shloka numbers like "॥१-१-१॥" (Devanagari digits)
RE_TRAILING_NUM = re.compile(r"॥\s*[\u0966-\u096F]+(?:[-–][\u0966-\u096F]+){1,2}\s*॥\s*$")
RE_DANDAS = re.compile(r"[।॥]")

def clean_shloka_line(line: str) -> str:
    # Strip the terminal "॥१-१-१॥" (or similar) if present at the end
    line = RE_TRAILING_NUM.sub("", line)
    # Remove all danda marks inside the line
    line = RE_DANDAS.sub("", line)
    return line.strip()

def determine_macro(n_lines: int) -> str:
    return {
        1: r"\onelineshloka",
        2: r"\twolineshloka",
        3: r"\threelineshloka",
        4: r"\fourlineindentedshloka",
    }.get(n_lines, r"\twolineshloka")

def get_sarga_title(kanda_num: int, sarga_num: int) -> str:
    """From ramayana_map.json: pick kanda by pos, then sarga by pos, return name_dev."""
    kanda = KANDA_BY_POS.get(kanda_num)
    if not kanda:
        return "अज्ञात"
    # 'list' is an array of sargas; each has 'pos' (1-based) and 'name_dev'
    # Use pos-1 to index if data is fully contiguous; else search by pos.
    if 1 <= sarga_num <= len(kanda.get("list", [])):
        entry = kanda["list"][sarga_num - 1]
        if entry.get("pos") == sarga_num:
            return entry.get("name_dev") or "अज्ञात"
    # fallback: search by pos
    for s in kanda.get("list", []):
        if s.get("pos") == sarga_num:
            return s.get("name_dev") or "अज्ञात"
    return "अज्ञात"

def build_sect_line(kanda_num: int, sarga_num: int) -> str:
    # “Ideally” you wanted ordinals (प्रथमः/द्वितीयः …). Since the map doesn’t include them,
    # we render: "<देवनागरी संख्या> सर्गः — <सर्ग-शीर्षक>"
    title_dev = get_sarga_title(kanda_num, sarga_num)
    return rf"\sect{{{to_devanagari(sarga_num)} सर्गः — {title_dev}}}"

def write_sarga_tex(kanda_num: int, sarga_json_path: Path) -> None:
    with sarga_json_path.open(encoding="utf-8") as f:
        records = json.load(f)  # list of {text, index, shloka_num or None}

    sarga_num = int(sarga_json_path.stem)  # "001" -> 1
    sect_line = build_sect_line(kanda_num, sarga_num)

    lines_out = [sect_line + "\n"]

    # Only the *last* unnumbered is the pushpika; others (e.g., the opening colophon) are ignored.
    last_unnumbered_idx = None
    for i, rec in enumerate(records):
        if rec.get("shloka_num") is None:
            last_unnumbered_idx = i

    for i, rec in enumerate(records):
        text = (rec.get("text") or "").strip()
        shno = rec.get("shloka_num")

        # pushpika: only if this is the final unnumbered record
        if shno is None:
            if i == last_unnumbered_idx and text:
                # Prefix exactly one "॥"
                t = text if text.lstrip().startswith("॥") else f"॥{text}"
                lines_out.append("\n" + t + "\n")
            # ignore earlier unnumbered records (like the header line)
            continue

        # Normal shloka
        raw_lines = [ln for ln in text.split("\n")]
        clean_lines = [cl for cl in (clean_shloka_line(ln) for ln in raw_lines) if cl]
        if not clean_lines:
            continue

        macro = determine_macro(len(clean_lines))
        lines_out.append(macro)
        for cl in clean_lines:
            lines_out.append("{" + cl + "}")
        # trailing comment with K-S-Ś numbers
        lines_out[-1] += f" %{kanda_num}-{sarga_num}-{shno}\n"

    # Output folder/name
    kanda_name, file_prefix = KANDA_EN.get(kanda_num, (f"Kanda{kanda_num}", f"kanda-{kanda_num}"))
    out_dir = TEX_DIR / f"{kanda_num}-{kanda_name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{file_prefix}-sarga-{sarga_num:03d}.tex"

    out_path.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"✅ {out_path}")

def main():
    # Walk src/data/<kanda_num>/*.json
    for kanda_dir in sorted(DATA_DIR.iterdir()):
        if not kanda_dir.is_dir():
            continue
        try:
            kanda_num = int(kanda_dir.name)
        except ValueError:
            continue

        for sargafile in sorted(kanda_dir.glob("*.json")):
            write_sarga_tex(kanda_num, sargafile)

if __name__ == "__main__":
    main()
