#!/usr/bin/env python3
"""Utilities to generate TeX files from the JSON data files.

The script expects the repository to contain a ``src/data`` directory that
houses JSON files for each kanda/sarga combination.  Each JSON file contains
shloka text that should be converted into the ``\\twolineshloka`` macro used by
our TeX sources.  The output is written into the ``TeX`` directory, mimicking
our LaTeX folder layout.

This module is intentionally defensive – the source JSON files were compiled
from multiple origins and can differ slightly in structure.  To remain robust
we look for commonly used keys when extracting shloka information and degrade
cleanly when a field is missing.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, MutableMapping, Optional, Sequence, Tuple

LOGGER = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("../src/data")
DEFAULT_OUTPUT_DIR = Path("TeX")
DEFAULT_MAP_FILE = DEFAULT_DATA_DIR / "ramayana_map.json"


@dataclass
class ShlokaEntry:
    """Container for shloka lines accompanied by an optional number."""

    lines: List[str]
    number: Optional[int]


@dataclass
class TitleIndex:
    """Helper class that stores lookup data for sarga titles."""

    by_slug: Dict[str, str]
    by_numbers: Dict[Tuple[int, int], str]

    @classmethod
    def from_map_file(cls, map_path: Path) -> "TitleIndex":
        if not map_path.exists():
            LOGGER.warning("Map file not found at %s – titles will be missing.", map_path)
            return cls({}, {})

        try:
            payload = json.loads(map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Unable to parse map file {map_path}: {exc}")

        index = cls({}, {})
        index._scan(payload)
        return index

    def _scan(self, node: object, *, inherited_kanda: Optional[int] = None) -> None:
        """Populate the lookup tables by recursively traversing *node*."""
        if isinstance(node, list):
            for item in node:
                self._scan(item, inherited_kanda=inherited_kanda)
            return

        if not isinstance(node, MutableMapping):
            return

        lower_key_map = {str(key).lower(): key for key in node.keys()}

        def _extract_int(keys: Iterable[str]) -> Optional[int]:
            for candidate in keys:
                if candidate in lower_key_map:
                    raw_value = node[lower_key_map[candidate]]
                    try:
                        return int(str(raw_value).strip())
                    except (TypeError, ValueError):
                        continue
            return None

        kanda_number = _extract_int(
            [
                "kanda_number",
                "kanda",
                "book_number",
                "book",
                "kanda_no",
                "kandaid",
            ]
        )
        if kanda_number is None:
            kanda_number = inherited_kanda

        sarga_number = _extract_int(
            [
                "sarga_number",
                "sarga",
                "chapter_number",
                "chapter",
                "adhyaya",
                "chapterid",
            ]
        )

        slug_value = None
        for key_name in ("slug", "chapter_slug", "sarga_slug", "id", "identifier"):
            key = lower_key_map.get(key_name)
            if key is None:
                continue
            raw_slug = node[key]
            if isinstance(raw_slug, str) and raw_slug.strip():
                slug_value = normalise_slug(raw_slug)
                break

        title_value = None
        for key_name in ("title", "chapter_title", "name", "heading"):
            key = lower_key_map.get(key_name)
            if key is None:
                continue
            raw_title = node[key]
            if isinstance(raw_title, str) and raw_title.strip():
                title_value = raw_title.strip()
                break

        if title_value:
            if slug_value:
                self.by_slug.setdefault(slug_value, title_value)
            if kanda_number is not None and sarga_number is not None:
                self.by_numbers.setdefault((kanda_number, sarga_number), title_value)

        for value in node.values():
            if isinstance(value, (list, MutableMapping)):
                self._scan(value, inherited_kanda=kanda_number)

    def get(self, slug: str, kanda_number: int, sarga_number: int) -> Optional[str]:
        slug_key = normalise_slug(slug)
        if slug_key in self.by_slug:
            return self.by_slug[slug_key]
        return self.by_numbers.get((kanda_number, sarga_number))


def normalise_slug(value: str) -> str:
    """Return a lower-case slug with hyphen separators."""
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", camel_split)
    cleaned = cleaned.strip("-")
    return cleaned.lower()


def iter_data_files(data_dir: Path) -> Iterator[Path]:
    if not data_dir.exists():
        LOGGER.error("Data directory %s does not exist.", data_dir)
        return

    for path in sorted(data_dir.rglob("*.json")):
        if path.name == DEFAULT_MAP_FILE.name:
            continue
        yield path


def extract_kanda_metadata(path: Path) -> Tuple[int, str, str]:
    """Return (kanda_number, kanda_slug, output_dir_name)."""
    try:
        parent_name = path.parent.name
    except IndexError:
        raise SystemExit(f"Unexpected file layout for {path}")

    match = re.match(r"^(\d+)[-_](.+)$", parent_name)
    if not match:
        raise SystemExit(
            f"Unable to derive kanda metadata from directory name '{parent_name}'"
        )

    kanda_number = int(match.group(1))
    kanda_slug = normalise_slug(match.group(2))
    pretty_name_parts = []
    for part in match.group(2).split('-'):
        if not part:
            continue
        pretty_name_parts.append(part[:1].upper() + part[1:])
    output_dir_name = f"{kanda_number}-{''.join(pretty_name_parts)}"
    return kanda_number, kanda_slug, output_dir_name


def extract_sarga_number(path: Path) -> int:
    match = re.search(r"(\d+)(?=\.[^./]+$)", path.name)
    if not match:
        raise SystemExit(f"Unable to determine sarga number from file name '{path.name}'")
    return int(match.group(1))


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Unable to parse JSON file {path}: {exc}")


CANDIDATE_TEXT_KEYS = (
    "text",
    "lines",
    "text_lines",
    "shloka",
    "sloka",
    "content",
    "values",
)

CANDIDATE_NUMBER_KEYS = (
    "number",
    "shloka_number",
    "shloka_no",
    "sloka_number",
    "sloka_no",
    "verse_number",
    "verse",
    "id",
    "identifier",
    "index",
)


def _coerce_int(value: object) -> Optional[int]:
    if isinstance(value, bool):  # guard against bool being subclass of int
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        matches = re.findall(r"\d+", value)
        if matches:
            try:
                return int(matches[-1])
            except ValueError:
                return None
    return None


def extract_shloka_number(shloka: object) -> Optional[int]:
    if not isinstance(shloka, MutableMapping):
        return None

    lower_key_map = {str(key).lower(): key for key in shloka.keys()}
    for candidate in CANDIDATE_NUMBER_KEYS:
        key = lower_key_map.get(candidate)
        if key is None:
            continue
        number = _coerce_int(shloka[key])
        if number is not None:
            return number

    for value in shloka.values():
        if isinstance(value, MutableMapping):
            number = extract_shloka_number(value)
            if number is not None:
                return number

    return None


def extract_shloka_lines(shloka: object) -> List[str]:
    if isinstance(shloka, str):
        return [line.strip() for line in shloka.splitlines() if line.strip()]

    if isinstance(shloka, MutableMapping):
        value: object
        for key in CANDIDATE_TEXT_KEYS:
            if key in shloka:
                value = shloka[key]
                break
        else:
            for key, value in shloka.items():
                if key.lower().endswith("_sanskrit") and isinstance(value, (str, list)):
                    break
            else:
                return []

        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(shloka, Sequence):
        return [str(item).strip() for item in shloka if str(item).strip()]

    return []


def extract_shloka_entry(shloka: object) -> ShlokaEntry:
    lines = extract_shloka_lines(shloka)
    number = extract_shloka_number(shloka)
    return ShlokaEntry(lines=lines, number=number)


def find_shlokas(data: object) -> List[ShlokaEntry]:
    if isinstance(data, list):
        return [extract_shloka_entry(item) for item in data]

    if isinstance(data, MutableMapping):
        for key in ("shlokas", "slokas", "verses", "data", "items", "content"):
            if key in data and isinstance(data[key], list):
                return [extract_shloka_entry(item) for item in data[key]]
        return [
            extract_shloka_entry(value)
            for value in data.values()
            if isinstance(value, (list, MutableMapping, str))
        ]

    return []


TEX_SPECIAL_CHARS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(value: str) -> str:
    result = []
    for char in value:
        if char in TEX_SPECIAL_CHARS:
            result.append(TEX_SPECIAL_CHARS[char])
        else:
            result.append(char)
    return "".join(result)


MACRO_BY_LINE_COUNT = {
    1: "onelineshloka",
    2: "twolineshloka",
    3: "threelineshloka",
}


def build_macro_segments(lines: Sequence[str]) -> List[Tuple[str, List[str]]]:
    """Split *lines* into macro segments.

    Ideally a single macro matches the shloka's line count.  When the number of
    lines exceeds the available macros we emit multiple segments, favouring
    two-line macros to preserve pada structure.
    """

    if not lines:
        return []

    segments: List[Tuple[str, List[str]]] = []
    index = 0
    total = len(lines)

    while index < total:
        remaining = total - index
        if remaining in MACRO_BY_LINE_COUNT:
            size = remaining
        elif remaining > 3:
            size = 2
        else:
            size = remaining

        macro_name = MACRO_BY_LINE_COUNT.get(size)
        if macro_name is None:
            LOGGER.warning(
                "Unsupported line count (%d) in shloka; defaulting to twolineshloka.",
                size,
            )
            macro_name = "twolineshloka"
            size = min(2, remaining) or 1

        segment_lines = [lines[index + offset] for offset in range(size)]
        segments.append((macro_name, segment_lines))
        index += size

    return segments


def format_shloka_macro(macro_name: str, lines: Sequence[str], comment: Optional[str]) -> str:
    body: List[str] = [f"\\{macro_name}"]
    for idx, line in enumerate(lines, start=1):
        suffix = ""
        if comment and idx == len(lines):
            suffix = f" %{comment}"
        body.append(f"{{{tex_escape(line)}}}{suffix}")
    return "\n".join(body)


def generate_tex_content(
    *,
    source_path: Path,
    shlokas: List[ShlokaEntry],
    kanda_number: int,
    sarga_number: int,
    title_index: TitleIndex,
    kanda_slug: str,
) -> str:
    slug = f"{kanda_slug}-sarga-{sarga_number:03d}"
    title = title_index.get(slug, kanda_number, sarga_number)

    lines: List[str] = []
    lines.append(f"% Auto-generated from {source_path.as_posix()}")
    lines.append(f"% Generated on {datetime.utcnow().isoformat()}Z")
    if title:
        lines.append(f"\\chapter{{{tex_escape(title)}}}")
    else:
        lines.append(f"% Title not available for {slug}")
    lines.append("")

    for entry_index, entry in enumerate(shlokas, start=1):
        if not entry.lines:
            continue

        shloka_number = entry.number if entry.number is not None else entry_index
        identifier = f"{kanda_number}-{sarga_number:03d}-{shloka_number:03d}"

        segments = build_macro_segments(entry.lines)
        if not segments:
            continue

        if len(segments) > 1 or len(entry.lines) not in MACRO_BY_LINE_COUNT:
            LOGGER.warning(
                "Shloka entry %d (number %s) in %s contains %d lines; emitted %d macro segments.",
                entry_index,
                entry.number if entry.number is not None else "unknown",
                source_path,
                len(entry.lines),
                len(segments),
            )

        for segment_index, (macro_name, macro_lines) in enumerate(segments, start=1):
            comment = identifier if segment_index == len(segments) else None
            lines.append(format_shloka_macro(macro_name, macro_lines, comment))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def process_file(
    path: Path,
    *,
    output_dir: Path,
    title_index: TitleIndex,
    overwrite: bool,
) -> Optional[Path]:
    data = read_json(path)
    shlokas = find_shlokas(data)
    shlokas = [entry for entry in shlokas if entry.lines]
    if not shlokas:
        LOGGER.warning("No shloka data detected in %s", path)
        return None

    kanda_number, kanda_slug, kanda_output_dir_name = extract_kanda_metadata(path)
    sarga_number = extract_sarga_number(path)

    output_path = output_dir / kanda_output_dir_name / f"{kanda_slug}-sarga-{sarga_number:03d}.tex"

    if output_path.exists() and not overwrite:
        LOGGER.info("Skipping existing file %s", output_path)
        return output_path

    content = generate_tex_content(
        source_path=path,
        shlokas=shlokas,
        kanda_number=kanda_number,
        sarga_number=sarga_number,
        title_index=title_index,
        kanda_slug=kanda_slug,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    LOGGER.info("Wrote %s", output_path)
    return output_path


def run(*, data_dir: Path, output_dir: Path, map_file: Path, overwrite: bool) -> int:
    title_index = TitleIndex.from_map_file(map_file)

    processed = 0
    for json_file in iter_data_files(data_dir):
        if process_file(json_file, output_dir=output_dir, title_index=title_index, overwrite=overwrite):
            processed += 1

    LOGGER.info("Generated %d TeX files", processed)
    return processed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TeX files from Valmiki Ramayana JSON data")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Path to the directory that contains the JSON source files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write the generated TeX files",
    )
    parser.add_argument(
        "--map-file",
        type=Path,
        default=DEFAULT_MAP_FILE,
        help="Path to ramayana_map.json containing sarga titles",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate files even if the target TeX file already exists",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    processed = run(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        map_file=args.map_file,
        overwrite=args.overwrite,
    )
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
