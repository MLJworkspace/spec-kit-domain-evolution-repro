#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


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
    return {entity.get("name", ""): entity for entity in model.get("entities", [])}


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
    return {relationship_key(rel): rel for rel in model.get("relationships", [])}


def relationship_stv_index(model: Dict[str, Any]) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    out: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for rel in model.get("relationships", []):
        out.setdefault(relationship_stv_key(rel), []).append(rel)
    return out


def sorted_unique(values: Iterable[str]) -> List[str]:
    return sorted({value for value in values if value})


def find_entity_decision(rationale: Dict[str, Any], generated_name: str) -> Optional[Dict[str, Any]]:
    for decision in rationale.get("entity_decisions", []) or []:
        if decision.get("generated_name") == generated_name:
            return decision
    return None


def find_attribute_decision(rationale: Dict[str, Any], entity: str, attribute: str) -> Optional[Dict[str, Any]]:
    for decision in rationale.get("attribute_decisions", []) or []:
        if decision.get("entity") == entity and decision.get("attribute") == attribute:
            return decision
    return None


def find_relationship_decision(
    rationale: Dict[str, Any], rel: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    key = relationship_key(rel)
    for decision in rationale.get("relationship_decisions", []) or []:
        decision_key = (
            decision.get("source_entity", ""),
            normalize_verb(decision.get("verb", "")),
            decision.get("target_entity", ""),
            decision.get("cardinality", ""),
        )
        if decision_key == key:
            return decision
    return None


def with_source_tag(item: Dict[str, Any], tag: str) -> Dict[str, Any]:
    copied = dict(item)
    copied["sources"] = sorted_unique([*copied.get("sources", []), tag])
    return copied


def generate_delta(base: Dict[str, Any], next_model: Dict[str, Any], rationale: Dict[str, Any]) -> Dict[str, Any]:
    base_entities = entity_index(base)
    next_entities = entity_index(next_model)
    base_rels = relationship_index(base)
    next_rels = relationship_index(next_model)
    base_rels_by_stv = relationship_stv_index(base)

    added_entities: List[Dict[str, Any]] = []
    reused_entities: List[Dict[str, Any]] = []
    modified_entities: List[Dict[str, Any]] = []
    retained_absent_entities: List[str] = []

    for name, next_entity in sorted(next_entities.items()):
        decision = find_entity_decision(rationale, name) or {}
        decision_value = decision.get("decision", "")
        if name in base_entities:
            base_attrs = set(base_entities[name].get("attributes", []))
            next_attrs = set(next_entity.get("attributes", []))
            new_attrs = sorted(next_attrs - base_attrs)
            reused_entities.append(
                {
                    "name": name,
                    "decision": decision_value or "reused",
                    "new_attributes": new_attrs,
                    "rationale": decision,
                }
            )
            if new_attrs:
                modified_entities.append(
                    {
                        "name": name,
                        "change_type": "attribute_extension",
                        "new_attributes": new_attrs,
                        "rationale": decision,
                    }
                )
        elif decision_value == "reused_with_modification":
            modified_entities.append(
                {
                    "name": name,
                    "change_type": "renamed_or_alias_reuse",
                    "existing_name": decision.get("existing_name", ""),
                    "entity": with_source_tag(next_entity, "delta:reused_with_modification"),
                    "rationale": decision,
                }
            )
        else:
            added_entities.append(
                {
                    "name": name,
                    "entity": with_source_tag(next_entity, "delta:added"),
                    "rationale": decision,
                }
            )

    for name in sorted(set(base_entities) - set(next_entities)):
        retained_absent_entities.append(name)

    added_attributes: List[Dict[str, Any]] = []
    for name, next_entity in sorted(next_entities.items()):
        base_attrs = set(base_entities.get(name, {}).get("attributes", []))
        for attr in sorted(set(next_entity.get("attributes", [])) - base_attrs):
            added_attributes.append(
                {
                    "entity": name,
                    "attribute": attr,
                    "rationale": find_attribute_decision(rationale, name, attr) or {},
                }
            )

    added_relationships: List[Dict[str, Any]] = []
    modified_relationships: List[Dict[str, Any]] = []
    reused_relationships: List[Dict[str, Any]] = []
    retained_absent_relationships: List[Dict[str, Any]] = []

    for key, rel in sorted(next_rels.items()):
        if key in base_rels:
            reused_relationships.append(
                {"relationship": rel, "rationale": find_relationship_decision(rationale, rel) or {}}
            )
            continue

        stv_key = relationship_stv_key(rel)
        if stv_key in base_rels_by_stv:
            modified_relationships.append(
                {
                    "change_type": "cardinality_change",
                    "base_relationships": base_rels_by_stv[stv_key],
                    "next_relationship": with_source_tag(rel, "delta:modified"),
                    "rationale": find_relationship_decision(rationale, rel) or {},
                }
            )
        else:
            added_relationships.append(
                {
                    "relationship": with_source_tag(rel, "delta:added"),
                    "rationale": find_relationship_decision(rationale, rel) or {},
                }
            )

    for key, rel in sorted(base_rels.items()):
        if key not in next_rels:
            retained_absent_relationships.append(rel)

    return {
        "delta_type": "feature_domain_delta",
        "base_source_spec": base.get("source_spec", ""),
        "next_source_spec": next_model.get("source_spec", ""),
        "rationale_source_spec": rationale.get("source_spec", ""),
        "summary": {
            "added_entity_count": len(added_entities),
            "modified_entity_count": len(modified_entities),
            "added_attribute_count": len(added_attributes),
            "added_relationship_count": len(added_relationships),
            "modified_relationship_count": len(modified_relationships),
            "retained_absent_entity_count": len(retained_absent_entities),
            "retained_absent_relationship_count": len(retained_absent_relationships),
        },
        "entities": {
            "added": added_entities,
            "reused": reused_entities,
            "modified": modified_entities,
            "retained_absent": retained_absent_entities,
        },
        "attributes": {
            "added": added_attributes,
        },
        "relationships": {
            "added": added_relationships,
            "reused": reused_relationships,
            "modified": modified_relationships,
            "retained_absent": retained_absent_relationships,
        },
        "warnings": [
            *(base.get("warnings", []) or []),
            *(next_model.get("warnings", []) or []),
            *(rationale.get("warnings", []) or []),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a feature-scoped domain delta.")
    parser.add_argument("--base", required=True, type=Path, help="Base feature-domain.json")
    parser.add_argument("--next", required=True, type=Path, help="Next feature-domain.json")
    parser.add_argument("--rationale", required=True, type=Path, help="domain-rationale.json for the next model")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output domain-delta.json")
    args = parser.parse_args()

    delta = generate_delta(load_json(args.base), load_json(args.next), load_json(args.rationale))
    write_json(args.output, delta)
    print(json.dumps(delta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
