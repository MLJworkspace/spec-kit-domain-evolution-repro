#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SECTION_RE = re.compile(r"^##+\s+(.+?)\s*$")
FR_RE = re.compile(r"^-\s+\*\*(FR-\d+)\*\*:\s*(.+?)\s*$")
ENTITY_RE = re.compile(r"^-\s+\*\*(?P<name>[^*]+?)\*\*:\s*(?P<description>.+?)\s*$")
BOLD_RE = re.compile(r"\*\*([^*]+?)\*\*")
CODE_RE = re.compile(r"`([^`]+?)`")

CARDINALITY = r"(exactly one|zero or one|one or more|zero or more|at least \d+|at most \d+)"
REL_RE = re.compile(
    rf"^(?:A|An|Each) \*\*(?P<src>[^*]+?)\*\* MUST "
    rf"(?P<verb>.+?) (?P<card>{CARDINALITY})"
    rf"(?: instances? of)? \*\*(?P<tgt>[^*]+?)\*\*\.?$",
    re.IGNORECASE,
)
REL_CLAUSE_RE = re.compile(
    rf"\b(?P<verb>belong(?:s|ing)? to|contain(?:s|ing)?|reference(?:s|ing)?|own(?:s|ing)?|"
    rf"has|have|having|be assigned to|be associated with|be reviewed by|"
    rf"place(?:s|ing)?|create(?:s|ing)?|submit(?:s|ting)?|request(?:s|ing)?|"
    rf"review(?:s|ing)?|approve(?:s|ing)?|reject(?:s|ing)?)\b"
    rf"\s+(?P<card>{CARDINALITY})"
    rf"(?:\s+(?:existing|instances? of|instance of))?"
    rf"\s+\*\*(?P<tgt>[^*]+?)\*\*",
    re.IGNORECASE,
)
ATTR_RE = re.compile(
    r"^The system MUST store a[n]? \*\*(?P<owner>[^*]+?)\*\* with (?P<attrs>.+?)\.?$",
    re.IGNORECASE,
)

VERB_NORMALIZATION = {
    "belongs to": "belong to",
    "belonging to": "belong to",
    "contains": "contain",
    "containing": "contain",
    "references": "reference",
    "referencing": "reference",
    "owns": "own",
    "owning": "own",
    "has": "be associated with",
    "have": "be associated with",
    "having": "be associated with",
    "places": "place",
    "placing": "place",
    "creates": "create",
    "creating": "create",
    "submits": "submit",
    "submitting": "submit",
    "requests": "request",
    "requesting": "request",
    "reviews": "review",
    "reviewing": "review",
    "approves": "approve",
    "approving": "approve",
    "rejects": "reject",
    "rejecting": "reject",
}


def strip_md_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def collect_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    level = None
    for i, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match and match.group(1).strip().startswith(heading):
            start = i + 1
            level = len(line) - len(line.lstrip("#"))
            break
    if start is None:
        return ""

    out: List[str] = []
    for line in lines[start:]:
        match = SECTION_RE.match(line)
        if match:
            this_level = len(line) - len(line.lstrip("#"))
            if this_level <= level:
                break
        out.append(line)
    return "\n".join(out)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def normalize_cardinality(cardinality: str) -> str:
    value = cardinality.lower().strip()
    mapping = {
        "exactly one": "1",
        "zero or one": "0..1",
        "one or more": "1..*",
        "zero or more": "0..*",
    }
    return mapping.get(value, value)


def normalize_verb(verb: str) -> str:
    value = " ".join(verb.lower().strip().split())
    return VERB_NORMALIZATION.get(value, value)


def add_unique(items: List[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def unique_dicts(items: Iterable[Dict], key_fields: Tuple[str, ...]) -> List[Dict]:
    seen = set()
    out = []
    for item in items:
        key = tuple(item.get(k, "") for k in key_fields)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def add_entity(
    entities: Dict[str, Dict],
    name: str,
    source: str,
    description: str = "",
    attributes: Iterable[str] = (),
) -> None:
    entity_name = normalize_name(name)
    if not entity_name:
        return
    entity = entities.setdefault(
        entity_name,
        {"name": entity_name, "description": "", "attributes": [], "sources": []},
    )
    if description and not entity["description"]:
        entity["description"] = description.strip()
    for attr in attributes:
        add_unique(entity["attributes"], attr.strip())
    add_unique(entity["sources"], source)


def parse_functional_requirements(section: str) -> List[Tuple[str, str]]:
    requirements: List[Tuple[str, str]] = []
    for line in section.splitlines():
        match = FR_RE.match(line.strip())
        if match:
            requirements.append((match.group(1), match.group(2).strip()))
    return requirements


def parse_key_entities(section: str, entities: Dict[str, Dict]) -> List[str]:
    warnings: List[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        match = ENTITY_RE.match(line)
        if not match:
            if BOLD_RE.search(line):
                warnings.append(f"Key Entities line did not match expected form: {line}")
            continue
        name = normalize_name(match.group("name"))
        description = match.group("description").strip()
        attrs = CODE_RE.findall(description)
        add_entity(entities, name, "Key Entities", description, attrs)
    return warnings


def bold_spans(sentence: str) -> List[Tuple[int, int, str]]:
    return [(m.start(), m.end(), normalize_name(m.group(1))) for m in BOLD_RE.finditer(sentence)]


def nearest_entity_before(spans: List[Tuple[int, int, str]], index: int) -> str:
    before = [span for span in spans if span[1] <= index]
    if not before:
        return ""
    return before[-1][2]


def add_relationship(
    relationships_by_key: Dict[Tuple[str, str, str, str], Dict],
    source: str,
    verb: str,
    target: str,
    cardinality: str,
    fr_id: str,
) -> None:
    key = (source, verb, target, cardinality)
    relationship = relationships_by_key.setdefault(
        key,
        {
            "source_entity": source,
            "verb": verb,
            "target_entity": target,
            "cardinality": cardinality,
            "sources": [],
        },
    )
    add_unique(relationship["sources"], fr_id)


def extract(spec_path: Path) -> Dict:
    raw = spec_path.read_text(encoding="utf-8")
    text = strip_md_comments(raw)

    requirements = collect_section(text, "Requirements")
    functional = collect_section(requirements, "Functional Requirements")
    key_entities = collect_section(requirements, "Key Entities")

    entities: Dict[str, Dict] = {}
    relationships_by_key: Dict[Tuple[str, str, str, str], Dict] = {}
    warnings: List[str] = []

    if not requirements:
        warnings.append("Missing '## Requirements' section.")
    if requirements and not functional:
        warnings.append("Missing '### Functional Requirements' subsection.")

    warnings.extend(parse_key_entities(key_entities, entities))

    for fr_id, sentence in parse_functional_requirements(functional):
        spans = bold_spans(sentence)
        for _, _, concept in spans:
            add_entity(entities, concept, fr_id)

        attr_match = ATTR_RE.match(sentence)
        attributes_extracted = False
        if attr_match:
            owner = normalize_name(attr_match.group("owner"))
            attrs = CODE_RE.findall(attr_match.group("attrs"))
            add_entity(entities, owner, fr_id, attributes=attrs)
            attributes_extracted = bool(attrs)
            continue

        for code_match in CODE_RE.finditer(sentence):
            owner = nearest_entity_before(spans, code_match.start())
            if owner:
                add_entity(entities, owner, fr_id, attributes=[code_match.group(1)])
                attributes_extracted = True

        rel_match = REL_RE.match(sentence)
        if rel_match:
            source = normalize_name(rel_match.group("src"))
            verb = normalize_verb(rel_match.group("verb"))
            target = normalize_name(rel_match.group("tgt"))
            cardinality = normalize_cardinality(rel_match.group("card"))

            add_entity(entities, source, fr_id)
            add_entity(entities, target, fr_id)
            add_relationship(relationships_by_key, source, verb, target, cardinality, fr_id)
            continue

        embedded_matches = list(REL_CLAUSE_RE.finditer(sentence))
        if embedded_matches:
            for match in embedded_matches:
                source = nearest_entity_before(spans, match.start())
                if not source:
                    continue
                verb = normalize_verb(match.group("verb"))
                target = normalize_name(match.group("tgt"))
                cardinality = normalize_cardinality(match.group("card"))
                add_entity(entities, source, fr_id)
                add_entity(entities, target, fr_id)
                add_relationship(relationships_by_key, source, verb, target, cardinality, fr_id)
            continue

        looks_like_missed_attribute = bool(CODE_RE.search(sentence)) and not attributes_extracted
        looks_like_missed_relationship = bool(BOLD_RE.search(sentence)) and bool(
            re.search(CARDINALITY, sentence, flags=re.IGNORECASE)
        )
        if looks_like_missed_attribute or looks_like_missed_relationship:
            warnings.append(
                f"{fr_id}: domain markers present but no entity attribute or relationship form matched: {sentence}"
            )

    return {
        "source_spec": str(spec_path),
        "entities": sorted(entities.values(), key=lambda x: x["name"]),
        "relationships": sorted(
            relationships_by_key.values(),
            key=lambda x: (
                x["source_entity"],
                x["verb"],
                x["target_entity"],
                x["cardinality"],
            ),
        ),
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path, help="Path to spec.md")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON path")
    args = parser.parse_args()

    model = extract(args.spec)
    data = json.dumps(model, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(data + "\n", encoding="utf-8")
    else:
        print(data)


if __name__ == "__main__":
    main()
