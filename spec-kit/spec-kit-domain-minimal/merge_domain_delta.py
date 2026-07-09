#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_verb(verb: str) -> str:
    return " ".join(str(verb).lower().strip().split())


def entity_index(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entity.get("name", ""): dict(entity) for entity in model.get("entities", [])}


def relationship_key(rel: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        rel.get("source_entity", ""),
        normalize_verb(rel.get("verb", "")),
        rel.get("target_entity", ""),
        rel.get("cardinality", ""),
    )


def relationship_stv_key(rel: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        rel.get("source_entity", ""),
        normalize_verb(rel.get("verb", "")),
        rel.get("target_entity", ""),
    )


def relationship_index(model: Dict[str, Any]) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    return {relationship_key(rel): dict(rel) for rel in model.get("relationships", [])}


def sorted_unique(values: Iterable[str]) -> List[str]:
    return sorted({value for value in values if value})


def merge_entity(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    if incoming.get("description") and not merged.get("description"):
        merged["description"] = incoming["description"]
    merged["attributes"] = sorted_unique([*merged.get("attributes", []), *incoming.get("attributes", [])])
    merged["sources"] = sorted_unique([*merged.get("sources", []), *incoming.get("sources", [])])
    return merged


def merge_relationship(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    merged["sources"] = sorted_unique([*merged.get("sources", []), *incoming.get("sources", [])])
    return merged


def merge_delta(base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    warnings = list(base.get("warnings", []) or [])
    warnings.extend(delta.get("warnings", []) or [])

    entities = entity_index(base)

    for added in delta.get("entities", {}).get("added", []) or []:
        entity = added.get("entity", {})
        name = entity.get("name", "")
        if not name:
            continue
        if name in entities:
            entities[name] = merge_entity(entities[name], entity)
            warnings.append(f"Delta added entity `{name}`, but it already existed in the base model; merged attributes and sources.")
        else:
            entities[name] = entity

    for modified in delta.get("entities", {}).get("modified", []) or []:
        if modified.get("change_type") == "attribute_extension":
            name = modified.get("name", "")
            if name in entities:
                entities[name]["attributes"] = sorted_unique(
                    [*entities[name].get("attributes", []), *modified.get("new_attributes", [])]
                )
                entities[name]["sources"] = sorted_unique([*entities[name].get("sources", []), "delta:attribute_extension"])
            else:
                warnings.append(f"Delta wanted to extend missing entity `{name}`; no entity was added.")
        elif modified.get("change_type") == "renamed_or_alias_reuse":
            entity = modified.get("entity", {})
            existing_name = modified.get("existing_name", "")
            if existing_name in entities:
                entities[existing_name] = merge_entity(entities[existing_name], entity)
                entities[existing_name]["sources"] = sorted_unique(
                    [*entities[existing_name].get("sources", []), "delta:renamed_or_alias_reuse"]
                )
            elif entity.get("name"):
                entities[entity["name"]] = entity
                warnings.append(
                    f"Delta mapped `{entity['name']}` to missing base entity `{existing_name}`; added generated entity instead."
                )

    relationships = relationship_index(base)

    for added in delta.get("relationships", {}).get("added", []) or []:
        rel = added.get("relationship", {})
        key = relationship_key(rel)
        if not all(key):
            continue
        if key in relationships:
            relationships[key] = merge_relationship(relationships[key], rel)
        else:
            relationships[key] = rel

    for modified in delta.get("relationships", {}).get("modified", []) or []:
        rel = modified.get("next_relationship", {})
        key = relationship_key(rel)
        if not all(key):
            continue
        same_stv_keys = [existing_key for existing_key in relationships if existing_key[:3] == relationship_stv_key(rel)]
        rationale_decision = (modified.get("rationale", {}) or {}).get("decision", "")
        if same_stv_keys and rationale_decision == "changed":
            for existing_key in same_stv_keys:
                relationships.pop(existing_key, None)
            relationships[key] = rel
            warnings.append(
                f"Applied explicit relationship change for `{rel.get('source_entity')} --{rel.get('verb')}--> {rel.get('target_entity')}`."
            )
        elif same_stv_keys:
            relationships[key] = rel
            warnings.append(
                f"Added changed relationship `{rel.get('source_entity')} --{rel.get('verb')} [{rel.get('cardinality')}]--> {rel.get('target_entity')}` without removing the base relationship because the rationale did not mark it as changed."
            )
        else:
            relationships[key] = rel

    shared = {
        "source_spec": f"shared-domain-model from {delta.get('base_source_spec', '')} + {delta.get('next_source_spec', '')}",
        "entities": sorted(entities.values(), key=lambda item: item.get("name", "")),
        "relationships": sorted(
            relationships.values(),
            key=lambda item: (
                item.get("source_entity", ""),
                normalize_verb(item.get("verb", "")),
                item.get("target_entity", ""),
                item.get("cardinality", ""),
            ),
        ),
        "warnings": sorted_unique(warnings),
    }
    return shared


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge a domain delta into a base model.")
    parser.add_argument("--base", required=True, type=Path, help="Base feature-domain.json")
    parser.add_argument("--delta", required=True, type=Path, help="domain-delta.json")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output shared-domain-model.json")
    args = parser.parse_args()

    shared = merge_delta(load_json(args.base), load_json(args.delta))
    write_json(args.output, shared)
    print(json.dumps(shared, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
