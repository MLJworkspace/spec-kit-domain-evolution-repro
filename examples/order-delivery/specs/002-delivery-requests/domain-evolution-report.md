# Domain Evolution Check Report

**Overall result:** Extension with reused/modified concepts

| Area | Result | Finding |
| --- | --- | --- |
| Shape | Pass | The base model has the required top-level fields. |
| Shape | Pass | The next model has the required top-level fields. |
| Shape | Pass | The rationale has the required decision sections. |
| Rationale | Pass | All rationale decision values are valid. |
| Entities | Pass | `Customer` is present in both models and rationale marks it as reused_with_modification. |
| Entities | Pass | `Delivery Request` is a new entity in the second model. |
| Entities | Pass | `Fulfillment Coordinator` is a new entity in the second model. |
| Entities | Pass | `Order` is present in both models and rationale marks it as reused. |
| Attributes | Pass | `Delivery Request.destination_address` is a new attribute in the second model. |
| Attributes | Pass | `Delivery Request.requested_delivery_date` is a new attribute in the second model. |
| Attributes | Pass | `Delivery Request.status` is a new attribute in the second model. |
| Relationships | Pass | `Customer --submit [0..*]--> Delivery Request` is an extension in the second model. |
| Relationships | Pass | `Delivery Request --be reviewed by [1]--> Fulfillment Coordinator` is an extension in the second model. |
| Relationships | Pass | `Delivery Request --belong to [1]--> Order` is an extension in the second model. |
| Relationships | Pass | `Fulfillment Coordinator --review [0..*]--> Delivery Request` is an extension in the second model. |
| Relationships | Pass | `Order --be associated with [0..1]--> Delivery Request` is an extension in the second model. |
| Conflicts | Pass | No contradictory cardinalities were found for existing relationships. |

## Issues

| Severity | Issue | Suggested fix |
| --- | --- | --- |
| None | No issues found. |  |

## Warnings

| Warning | Meaning |
| --- | --- |
| `Order Item` absent from second model | Allowed. The second model is feature-scoped, so absence is not treated as deletion. |
| `Product` absent from second model | Allowed. The second model is feature-scoped, so absence is not treated as deletion. |
