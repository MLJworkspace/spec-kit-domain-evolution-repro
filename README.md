# Spec Kit Domain Evolution Prototype

This repository contains a small reproducibility package for experimenting with domain model extraction and evolution in an LLM supported Spec Driven Development workflow.

The package includes an installable modified copy of GitHub Spec Kit, deterministic extraction and checking scripts, and one worked example with generated specifications and derived domain artifacts.

The prototype was run with Codex CLI 0.142.0 using GPT 5.5 medium in the local experimental environment.

## Minimal Example

The prototype links five kinds of artifacts:

```text
Spec Kit prompt
  -> generated spec.md
  -> extracted feature-domain.json
  -> generated domain-rationale.json for later features
  -> deterministic check, delta, and shared model
```

In the first feature, the modified `speckit-specify` command generates a normal natural language specification. The only addition is that important domain terms are marked in a parser-readable way inside the requirements:

```markdown
- The system MUST allow a **Customer** to create an **Order**.
- The system MUST prevent creating an **Order** unless the **Order** belongs to exactly one **Customer**.
```

The `extract_domain_model.py` script reads the generated `spec.md`, especially the Functional Requirements and Key Entities sections, and produces a JSON domain model with this shape:

```json
{
  "source_spec": "specs/001-order-management/spec.md",
  "entities": [
    {
      "name": "Customer",
      "description": "A person or account that creates Order instances.",
      "attributes": ["name", "contact_information"],
      "sources": ["Key Entities", "FR-001"]
    },
    {
      "name": "Order",
      "description": "A customer purchase request.",
      "attributes": ["status", "created_at", "total_amount"],
      "sources": ["Key Entities", "FR-001", "FR-002"]
    }
  ],
  "relationships": [
    {
      "source_entity": "Order",
      "verb": "belong to",
      "target_entity": "Customer",
      "cardinality": "1",
      "sources": ["FR-002"]
    }
  ],
  "warnings": []
}
```

In the second feature, the prompt provides the first domain model as context and deliberately uses a slightly different term:

```text
Add delivery requests where clients can request delivery for an existing order.
```

The modified `specify.md` command asks the LLM to generate two artifacts. First, it generates the second `spec.md`, where the prompt term `clients` is represented using the canonical existing entity name `Customer` when appropriate. Second, it generates `domain-rationale.json`, which explains the reuse decision:

```json
{
  "entity_decisions": [
    {
      "decision": "reused_with_modification",
      "existing_name": "Customer",
      "generated_name": "Customer",
      "prompt_term": "clients",
      "reason": "The prior model uses Customer for the party that creates orders."
    },
    {
      "decision": "new",
      "existing_name": "",
      "generated_name": "Delivery Request",
      "prompt_term": "delivery requests"
    }
  ]
}
```

The extractor then produces a second `feature-domain.json` containing the reused `Customer` and `Order` concepts plus new concepts and relationships such as:

```json
{
  "entities": [
    { "name": "Customer", "attributes": [], "sources": ["Key Entities", "FR-005"] },
    { "name": "Delivery Request", "attributes": ["destination_address", "requested_delivery_date", "status"], "sources": ["Key Entities", "FR-001"] },
    { "name": "Fulfillment Coordinator", "attributes": [], "sources": ["Key Entities", "FR-010"] }
  ],
  "relationships": [
    {
      "source_entity": "Customer",
      "verb": "submit",
      "target_entity": "Delivery Request",
      "cardinality": "0..*"
    },
    {
      "source_entity": "Delivery Request",
      "verb": "belong to",
      "target_entity": "Order",
      "cardinality": "1"
    }
  ]
}
```

Finally, `check_domain_evolution.py` compares the first and second domain models using the rationale as guidance. In the included run, it classifies the second model as an extension with reused and modified concepts. `generate_domain_delta.py` then records the added entities, attributes, and relationships. `merge_domain_delta.py` applies that delta to the first model and creates a separate `shared-domain-model.json`, without replacing the original first feature model.

## What Is In This Repository

| Path | Purpose |
|---|---|
| `spec-kit/` | Full modified Spec Kit source. This can be used with `uvx --from ./spec-kit specify init ...` to initialize a project that uses the modified workflow. |
| `spec-kit/templates/commands/specify.md` | Modified `specify` command. It keeps requirements natural language while guiding domain notation and rationale generation. |
| `spec-kit/spec-kit-domain-minimal/domain-metamodel.schema.json` | Minimal schema for extracted domain models. |
| `spec-kit/spec-kit-domain-minimal/domain-rationale.schema.json` | Schema for the machine-readable rationale generated for a later feature when an existing domain model is provided. |
| `spec-kit/spec-kit-domain-minimal/extract_domain_model.py` | Deterministic parser from `spec.md` to `feature-domain.json`. |
| `spec-kit/spec-kit-domain-minimal/check_domain_evolution.py` | Deterministic checker that compares two domain models using the rationale as guidance. It can generate Markdown and Word reports. |
| `spec-kit/spec-kit-domain-minimal/generate_domain_delta.py` | Generates a domain delta between the first and second domain models. |
| `spec-kit/spec-kit-domain-minimal/merge_domain_delta.py` | Merges the delta into the first model to create a shared domain model without replacing the first model. |
| `examples/order-delivery/` | Worked example with two generated feature specifications and all derived artifacts. |

## Worked Example

The included example has two features.

Feature 1 is an order management feature with customers, orders, order items, and products.

Feature 2 is a delivery request feature. It deliberately refers to `clients` rather than `customers`, reuses the existing order concept, and adds delivery requests and fulfillment coordinators.

The checker identifies that `clients` maps to the existing `Customer` concept, while `Delivery Request` and `Fulfillment Coordinator` are new concepts. It finds no conflicting cardinalities with the first domain model.

## Reproduce The Included Artifacts

From the repository root:

```bash
cd examples/order-delivery
bash reproduce_artifacts.sh
```

This regenerates:

```text
specs/001-order-management/feature-domain.json
specs/002-delivery-requests/feature-domain.json
specs/002-delivery-requests/domain-evolution-report.md
specs/002-delivery-requests/domain-delta.json
specs/shared-domain-model.json
```

If `python-docx` is installed, the script also regenerates:

```text
specs/002-delivery-requests/domain-evolution-report.docx
```

Install the optional Word dependency with:

```bash
python3 -m pip install python-docx
```

## Notes

This repository is an illustrative prototype. It demonstrates one possible interaction between LLM generated specifications, extracted domain models, rationale capture, deterministic consistency checking, delta generation, and controlled model evolution.

The schema and checking logic are intentionally minimal. They are not intended to be a finalized domain metamodel or complete consistency checking framework.
