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

DEFAULT_DATA_DIR = Path("src/data")
DEFAULT_OUTPUT_DIR = Path("TeX")
DEFAULT_MAP_FILE = DEFAULT_DATA_DIR / "ramayana_map.json"


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
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", value)
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
    output_dir_name = f"{kanda_number}-{''.join(part.capitalize() for part in match.group(2).split('-'))}"
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


def extract_shloka_lines(shloka: object) -> List[str]:
    if isinstance(shloka, str):
        return [line.strip() for line in shloka.splitlines() if line.strip()]

    if isinstance(shloka, MutableMapping):
        for key in CANDIDATE_TEXT_KEYS:
            if key in shloka:
                value = shloka[key]
                break
        else:
            # Some data sets nest the Sanskrit text under a dedicated field
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


def find_shlokas(data: object) -> List[List[str]]:
    if isinstance(data, list):
        return [extract_shloka_lines(item) for item in data]

    if isinstance(data, MutableMapping):
        for key in ("shlokas", "slokas", "verses", "data", "items", "content"):
            if key in data and isinstance(data[key], list):
                return [extract_shloka_lines(item) for item in data[key]]
        # Some JSON files might only contain the shloka data without a wrapper key.
        return [extract_shloka_lines(value) for value in data.values() if isinstance(value, (list, MutableMapping, str))]

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


def chunked(lines: Sequence[str], size: int = 2) -> Iterator[Tuple[str, ...]]:
    buffer: List[str] = []
    for line in lines:
        buffer.append(line)
        if len(buffer) == size:
            yield tuple(buffer)
            buffer.clear()
    if buffer:
        padded = list(buffer) + ["" for _ in range(size - len(buffer))]
        yield tuple(padded)


def format_twolineshloka(line_one: str, line_two: str, comment: str) -> str:
    return "\n".join(
        [
            "\\twolineshloka",
            f"{{{tex_escape(line_one)}}}",
            f"{{{tex_escape(line_two)}}} %{comment}",
        ]
    )


def generate_tex_content(
    *,
    source_path: Path,
    shlokas: List[List[str]],
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

    shloka_counter = 1
    for entry_index, entry in enumerate(shlokas, start=1):
        if not entry:
            continue
        if len(entry) % 2 != 0:
            LOGGER.warning(
                "Shloka %d in %s has an odd number of lines (%d); padding the last line.",
                entry_index,
                source_path,
                len(entry),
            )
        for pair in chunked(entry, 2):
            comment = f"{kanda_number}-{sarga_number}-{shloka_counter}"
            lines.append(format_twolineshloka(pair[0], pair[1], comment))
            lines.append("")
            shloka_counter += 1

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
    shlokas = [entry for entry in shlokas if entry]
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
