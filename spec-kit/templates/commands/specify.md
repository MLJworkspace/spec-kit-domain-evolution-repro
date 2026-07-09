---
description: Create or update the feature specification from a natural language feature description.
handoffs:
  - label: Build Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Clarify Spec Requirements
    agent: speckit.clarify
    prompt: Clarify specification requirements
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before specification)**:

- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under `hooks.before_specify`.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):

    ```text
    ## Extension Hooks
    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}
    Prompt: {prompt}
    To execute: `/{command}`
    ```

  - **Mandatory hook** (`optional: false`):

    ```text
    ## Extension Hooks
    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```

    Wait for the result of the hook command before proceeding to the Outline.

- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Outline

The text the user typed after `__SPECKIT_COMMAND_SPECIFY__` in the triggering message **is** the feature description. Assume you always have it available in this conversation even if `{ARGS}` appears literally below. Do not ask the user to repeat it unless they provided an empty command.

Given that feature description, do this:

1. **Generate a concise short name** (2-4 words) for the feature:
   - Analyze the feature description and extract the most meaningful keywords.
   - Create a 2-4 word short name that captures the essence of the feature.
   - Use action-noun format when possible, e.g., `user-auth`, `payment-timeout`, `analytics-dashboard`.
   - Preserve technical terms and acronyms, e.g., OAuth2, API, JWT.

2. **Branch creation** (optional, via hook):
   - If a `before_specify` hook ran successfully, it will have created/switched to a git branch and output JSON containing `BRANCH_NAME` and `FEATURE_NUM`.
   - Note these values for reference, but the branch name does **not** dictate the spec directory name.
   - If the user explicitly provided `GIT_BRANCH_NAME`, pass it through to the hook so the branch script uses the exact value as the branch name.

3. **Create the spec feature directory**:
   - Specs live under the default `specs/` directory unless the user explicitly provides `SPECIFY_FEATURE_DIRECTORY`.
   - Resolution order for `SPECIFY_FEATURE_DIRECTORY`:
     1. If the user explicitly provided `SPECIFY_FEATURE_DIRECTORY`, use it as-is.
     2. Otherwise, auto-generate it under `specs/`:
        - Check `.specify/init-options.json` for `feature_numbering`.
        - If `timestamp`: prefix is `YYYYMMDD-HHMMSS`.
        - If `sequential` or absent: prefix is `NNN`, the next available 3-digit number after scanning existing directories in `specs/`.
        - Construct the directory name: `<prefix>-<short-name>`.
   - `mkdir -p SPECIFY_FEATURE_DIRECTORY`.
   - Resolve the active `spec-template` through the Spec Kit preset/template resolution stack.
   - Copy the resolved `spec-template` file to `SPECIFY_FEATURE_DIRECTORY/spec.md` as the starting point.
   - Set `SPEC_FILE` to `SPECIFY_FEATURE_DIRECTORY/spec.md`.
   - Persist the resolved path to `.specify/feature.json`:

     ```json
     {
       "feature_directory": "SPECIFY_FEATURE_DIRECTORY"
     }
     ```

   - Write the actual resolved directory path value, e.g., `specs/003-user-auth`, not the literal string `SPECIFY_FEATURE_DIRECTORY`.

   **IMPORTANT**:
   - Create only one feature per `__SPECKIT_COMMAND_SPECIFY__` invocation.
   - The spec directory name and the git branch name are independent.
   - The spec directory and file are always created by this command, never by the hook.

4. Load the resolved active `spec-template` file to understand required sections.

5. **IF EXISTS**: Load `/memory/constitution.md` for project principles and governance constraints.

6. Parse the feature description:
   - If empty: ERROR `No feature description provided`.
   - Extract actors, user goals, actions, data, business rules, constraints, and external dependencies.
   - Make informed guesses based on context and industry standards.
   - Mark with `[NEEDS CLARIFICATION: specific question]` only when the choice significantly affects scope, security/privacy, user experience, or legal/compliance behavior and no reasonable default exists.
   - Use a maximum of 3 `[NEEDS CLARIFICATION]` markers total.

7. Fill `User Scenarios & Testing`:
   - Use user stories as independently testable vertical slices.
   - Keep stories plain-language and user-value oriented.
   - If no clear user flow exists: ERROR `Cannot determine user scenarios`.

8. Fill `Functional Requirements` with clear, testable, user- or business-observable requirements. Keep the normal Spec Kit meaning of "functional requirement" first. Use bold entity names and inline-code attributes consistently when they naturally appear, but do not turn the requirements list into a data model inventory.

9. Fill `Key Entities` if the feature involves data.

10. Fill `Success Criteria`:
    - Create measurable, technology-agnostic outcomes.
    - Include quantitative metrics and qualitative outcomes where appropriate.
    - Each criterion must be verifiable without implementation details.

11. Fill `Assumptions`:
    - Record reasonable defaults, external dependencies, scope boundaries, reused existing domain facts, and explicit domain evolution decisions when an existing domain model is provided.

12. Write the specification to `SPEC_FILE` using the template structure, replacing placeholders with concrete details derived from the feature description while preserving section order and headings.

## Requirement Domain Notation Rules

These rules apply only to the generated `Functional Requirements` and `Key Entities` sections.

Do **not** include this instruction section in the generated `spec.md`.

The spec must not contain a parser-only domain model section. The parser extracts a simple domain model directly from `Functional Requirements` and `Key Entities`. The extracted model contains only:

- domain entities
- attributes for each entity
- relationships between entities
- relationship cardinalities

Do not create a separate `Domain Model`, schema, JSON, ontology, or parser-output section in the spec.

### 1. Entity Names

An entity is a domain-level actor, object, record, event, workflow item, or business object relevant to the feature.

- Use singular, canonical, Title Case entity names.
- Mark entity names with bold Markdown: `**Customer**`, `**Order**`, `**Order Item**`.
- Use the exact same entity name everywhere.
- Do not introduce synonyms for the same entity.
- Do not include implementation entities such as tables, APIs, services, DTOs, classes, repositories, or storage records.

### 2. Attributes

An attribute is a named property of an entity.

- Mark attributes with inline code: `` `status` ``, `` `created_at` ``, `` `total_amount` ``.
- Use snake_case.
- Include only domain-relevant attributes.
- Do not include implementation identifiers, foreign keys, audit fields, or technical metadata unless the user prompt makes them part of the domain.

When a requirement naturally needs to name entity attributes, mark those attributes with inline code. Do not add a standalone storage requirement only to make the parser see attributes unless the user explicitly asked that the system must store or retain those fields.

```markdown
- **FR-###**: The system MUST require each **Order Item** to include a positive whole-number `quantity`.
```

Acceptable attribute-bearing examples:

```markdown
- **FR-004**: The system MUST require each **Order Item** to include a positive whole-number `quantity`.
- **FR-005**: The system MUST preserve the **Order Item** `unit_price` used when the **Order** is created.
```

### 3. Relationships And Cardinalities

Use only these cardinality phrases:

- `exactly one`
- `zero or one`
- `one or more`
- `zero or more`
- `at least [number]`
- `at most [number]`

When a functional requirement naturally includes a relationship and cardinality, express the cardinality clearly using one of the allowed phrases, but keep the sentence focused on user-visible or business-relevant behavior. Do not add standalone relationship requirements only to make the parser see the relationship if the same fact can be expressed as part of a user- or business-observable requirement.

```markdown
- **FR-###**: The system MUST allow a **Customer** to create an **Order** only when the **Order** contains one or more instances of **Order Item** and belongs to exactly one **Customer**.
```

Acceptable relationship-bearing examples:

```markdown
- **FR-002**: The system MUST allow a **Customer** to create an **Order** only when the **Order** belongs to exactly one **Customer**.
- **FR-003**: The system MUST prevent checkout for an **Order** unless the **Order** contains one or more instances of **Order Item**.
- **FR-004**: The system MUST prevent adding an **Order Item** unless the **Order Item** references exactly one existing **Product**.
- **FR-005**: The system MUST allow a **Customer** to submit zero or more instances of **Delivery Request** over time, provided each **Delivery Request** belongs to exactly one **Order**.
```

Preferred relationship verbs include `contain`, `reference`, `belong to`, `be assigned to`, `be associated with`, `be reviewed by`, `own`, `place`, `create`, `request`, `submit`, `review`, `approve`, and `reject`.

### 4. Functional Requirements

Functional requirements should stay readable and testable for product/business stakeholders. They should describe required system behavior, permissions, validations, calculations, preservation, visibility, feedback, or business outcomes. Prefer sentences that explain what the system allows, prevents, preserves, calculates, shows, or requires in a business workflow.

If a prompt actor performs an action on a domain object, represent that actor/object relationship in at least one functional requirement using bold canonical entity names and an allowed cardinality phrase. Do not leave the actor as plain text when it maps to an existing or new entity.

Do not write requirements that are merely a domain model list, such as:

```markdown
- **FR-###**: The system MUST store a **Customer** with `name`.
- **FR-###**: A **Customer** MUST create zero or more instances of **Order**.
```

Prefer functional versions:

```markdown
- **FR-###**: The system MUST prevent creating an **Order** unless the **Order** belongs to exactly one **Customer**.
- **FR-###**: The system MUST make **Order** ownership visible to authorized viewers of **Order** details.
```

Avoid phrasing that reads like a data model, even if it is technically parseable. A good requirement should still make sense to a stakeholder who does not care about extraction.

Do not force constraints, lifecycle states, state transitions, validation rules, policies, or workflows into parser-oriented forms. They may remain ordinary requirements, but the parser will not extract them into the domain model.

### 5. Key Entities

For `Key Entities`:

- Include one bullet for each important entity used in `Functional Requirements`.
- Use exact same bold entity names used in `Functional Requirements`.
- Keep descriptions domain-level and concise.
- Mention attributes using inline code only when they are part of the requirements.
- Mention relationships using exact bold entity names when useful.
- Do not include implementation entities.

The parser uses `Key Entities` for entity descriptions and additional attributes, but relationships and cardinalities are extracted from `Functional Requirements`.

### 6. Merging Repeated Mentions

It is okay for the same entity or relationship to be mentioned more than once across requirements. Use the same canonical name every time. The parser will merge repeated entity mentions, combine attributes for the same entity, and merge duplicate relationships while retaining their source requirement IDs.

### 7. Existing Domain Model Context, When Provided

If the user provides an existing domain model:

- Reuse existing entity names when the new prompt refers to the same domain thing.
- If the prompt uses a different term for an existing entity, keep the concept in the new spec using the canonical existing entity name and record it as `reused_with_modification` in the rationale. Example: if the prompt says "clients" and the existing model has **Customer**, write requirements using **Customer** when they clearly refer to the same actor.
- Do not drop a concept from the prompt because its name differs from the prior model. Every domain actor or object named in the prompt must be represented as one of: `reused`, `reused_with_modification`, or `new`.
- Reuse existing attribute names when the same property is needed.
- Reuse existing relationship wording and cardinality when the new prompt is consistent with it.
- Add new entities, attributes, and relationships when the new prompt genuinely extends the domain.
- If the new prompt conflicts with an existing relationship or cardinality and does not explicitly request a change, add `[NEEDS CLARIFICATION: ...]`.
- Do not copy the old domain model wholesale into the new spec; include only entities and relationships relevant to the current feature.
- You may leave unrelated prior-model entities out of the new spec, but do not add rationale entries for unrelated omissions. The rationale should explain active decisions for prompt concepts and relevant prior-model concepts only.

When an existing domain model is provided, also create `SPECIFY_FEATURE_DIRECTORY/domain-rationale.json`. This file is for deterministic consistency checking and must be valid JSON only, with no markdown fence or commentary.

Use this exact top-level shape:

```json
{
  "source_spec": "SPEC_FILE",
  "input_domain_model": "path or inline description of the provided model",
  "summary": "one-sentence summary of how prior domain context was used",
  "entity_decisions": [],
  "attribute_decisions": [],
  "relationship_decisions": [],
  "conflicts": [],
  "warnings": []
}
```

For each entity considered from the prompt or prior model, add an `entity_decisions` item:

```json
{
  "decision": "reused | reused_with_modification | new",
  "existing_name": "existing entity name, or empty string",
  "generated_name": "entity name used in the new spec, or empty string",
  "prompt_term": "term from the user prompt, or empty string",
  "reason": "short reason",
  "evidence": "brief quote or reference from prompt/domain model"
}
```

For each relevant attribute, add an `attribute_decisions` item:

```json
{
  "decision": "reused | reused_with_modification | new",
  "entity": "entity name",
  "attribute": "attribute_name",
  "reason": "short reason",
  "evidence": "brief quote or reference from prompt/domain model"
}
```

For each relevant relationship, add a `relationship_decisions` item:

```json
{
  "decision": "reused | reused_with_modification | new | changed",
  "source_entity": "source entity",
  "verb": "relationship verb",
  "target_entity": "target entity",
  "cardinality": "1 | 0..1 | 1..* | 0..* | at least N | at most N",
  "reason": "short reason",
  "evidence": "brief quote or reference from prompt/domain model"
}
```

For each conflict or possible conflict, add a `conflicts` item:

```json
{
  "kind": "entity | attribute | relationship | cardinality",
  "existing_fact": "fact from prior domain model",
  "requested_fact": "fact requested or implied by the prompt",
  "resolution": "clarification_required | explicit_evolution | no_conflict",
  "evidence": "brief quote or reference"
}
```

Use empty arrays when there are no items. Do not include implementation details. Do not include chain-of-thought; `reason` must be a concise audit reason only.

## Specification Quality Validation

After writing the initial spec, validate it against quality criteria.

### Create Spec Quality Checklist

Generate a checklist file at `SPECIFY_FEATURE_DIRECTORY/checklists/requirements.md` using this structure:

```markdown
# Specification Quality Checklist: [FEATURE NAME]

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: [DATE]
**Feature**: [Link to spec.md]

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Success criteria are technology-agnostic
- [ ] All acceptance scenarios are defined
- [ ] Edge cases are identified
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

## Domain Notation Quality

- [ ] Entity names in Functional Requirements and Key Entities use bold Markdown, singular Title Case, and no synonym drift
- [ ] Every domain actor or object named in the prompt is represented in the requirements as an existing canonical entity, a renamed/reused entity, or a new entity
- [ ] Entity attributes use inline code and snake_case
- [ ] Relationship requirements use one of the allowed cardinality phrases
- [ ] Key Entities contains concise descriptions for important entities
- [ ] No implementation entities appear in Functional Requirements or Key Entities

## Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
- [ ] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `__SPECKIT_COMMAND_CLARIFY__` or `__SPECKIT_COMMAND_PLAN__`
```

### Run Validation Check

Review the spec against each checklist item:

- For each item, determine if it passes or fails.
- Document specific issues found, quoting relevant spec sections.
- If a relationship or attribute requirement does not follow the prescribed parser-readable form, revise it.
- If a concept appears both bolded and unbolded with the same meaning, revise it.
- If two names appear to refer to the same concept, select one canonical name and revise the spec to use it consistently.
- If all items pass, mark checklist complete and proceed to hooks.
- If items fail, update the spec and re-run validation up to 3 iterations.
- If `[NEEDS CLARIFICATION]` markers remain, present at most 3 clarification questions to the user following the existing Spec Kit clarification format.

## Mandatory Post-Execution Hooks

You **MUST** complete this section before reporting completion to the user.

Check if `.specify/extensions.yml` exists in the project root.

- If it does not exist, or no hooks are registered under `hooks.after_specify`, skip to the Completion Report.
- If it exists, read it and look for entries under `hooks.after_specify`.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue to the Completion Report.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
- For each executable hook, output the following based on its `optional` flag:
  - **Mandatory hook** (`optional: false`) — emit `EXECUTE_COMMAND:` for each mandatory hook:

    ```text
    ## Extension Hooks
    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```

  - **Optional hook** (`optional: true`):

    ```text
    ## Extension Hooks
    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}
    Prompt: {prompt}
    To execute: `/{command}`
    ```

## Completion Report

Report completion to the user with:

- `SPECIFY_FEATURE_DIRECTORY` — the feature directory path
- `SPEC_FILE` — the spec file path
- `DOMAIN_RATIONALE_FILE` — the domain rationale path, only if an existing domain model was provided
- Checklist results summary
- Readiness for the next phase: `__SPECKIT_COMMAND_CLARIFY__` or `__SPECKIT_COMMAND_PLAN__`

## Quick Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement: no tech stack, APIs, code structure, database details, services, frameworks, classes, or infrastructure.
- Write for business stakeholders, not developers.
- Do not create checklists embedded in the spec; the checklist is a separate file.
- Make informed guesses where reasonable and document them in Assumptions.
- Limit clarifications to a maximum of 3.
- Think like a tester: every vague requirement should fail the testable and unambiguous checklist item.

## Done When

- [ ] Specification written to `SPEC_FILE` and validated against the quality checklist
- [ ] Extension hooks dispatched or skipped according to the rules above
- [ ] Completion reported to user with feature directory, spec file path, and checklist results
