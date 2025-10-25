#!/bin/bash
find . -type f -name '*.json' | while read -r x; do   base=$(basename "$x")           # e.g. 001.json
  num=${base%.json}               # -> 001
  num=$((10#$num))                # strip leading zeros (001 -> 1)
  target="../../../thesanskritchannel_projects/data/1. ramayanam/data/$(dirname "$x")/${num}.json";   mkdir -p "$(dirname "$target")" # ensure subfolders exist
  cp "$x" "$target"; done
