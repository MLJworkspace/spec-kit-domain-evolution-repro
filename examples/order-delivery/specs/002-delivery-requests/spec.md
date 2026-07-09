# Feature Specification: Delivery Requests

**Feature Branch**: `[002-delivery-requests]`  
**Created**: 2026-07-08  
**Status**: Draft  
**Input**: User description: "Read and use the existing domain model at specs/001-order-management/feature-domain.json as prior domain context. Add delivery requests where clients can request delivery for an existing order, each order can have zero or one delivery request, fulfillment coordinators can review delivery requests, and delivery requests include a destination address and requested delivery date."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request Delivery for an Order (Priority: P1)

A **Customer** requests delivery for an existing **Order** by providing the delivery destination and the date they want delivery to occur.

**Why this priority**: This is the core value of the feature: a customer can attach delivery needs to an order that already exists.

**Independent Test**: Start with an existing **Order** that has no **Delivery Request**, submit a destination address and requested delivery date, and verify the request is created and visible from the order details.

**Acceptance Scenarios**:

1. **Given** an existing **Order** with zero **Delivery Request** records, **When** the **Customer** submits a destination address and requested delivery date, **Then** the system records one **Delivery Request** for that **Order**.
2. **Given** an existing **Order** that already has one **Delivery Request**, **When** the **Customer** tries to submit another delivery request for the same **Order**, **Then** the system prevents the duplicate request and explains that the order already has a delivery request.

---

### User Story 2 - Review Delivery Requests (Priority: P2)

A **Fulfillment Coordinator** reviews submitted **Delivery Request** details so fulfillment can decide whether the requested delivery can be handled.

**Why this priority**: Delivery requests need operational review before they can guide fulfillment work.

**Independent Test**: Start with a submitted **Delivery Request**, review it as a **Fulfillment Coordinator**, record a review outcome, and verify the outcome is visible to authorized viewers.

**Acceptance Scenarios**:

1. **Given** a submitted **Delivery Request**, **When** a **Fulfillment Coordinator** approves it, **Then** the system marks the request as approved and identifies it as reviewed.
2. **Given** a submitted **Delivery Request**, **When** a **Fulfillment Coordinator** rejects it, **Then** the system marks the request as rejected and preserves the original destination address and requested delivery date.

---

### User Story 3 - View Delivery Request Status on an Order (Priority: P3)

Authorized viewers of an **Order** can see whether the order has a delivery request and, if present, the current delivery request details and review status.

**Why this priority**: Customers and fulfillment staff need a shared view of delivery expectations without searching outside the order context.

**Independent Test**: View order details for orders with and without delivery requests and verify that delivery request presence, destination, requested date, and review status are displayed accurately.

**Acceptance Scenarios**:

1. **Given** an **Order** with zero **Delivery Request** records, **When** an authorized viewer opens the order details, **Then** the system shows that no delivery request has been submitted.
2. **Given** an **Order** with one **Delivery Request**, **When** an authorized viewer opens the order details, **Then** the system shows the delivery destination, requested delivery date, and current review status.

---

### Edge Cases

- A **Customer** attempts to request delivery for an **Order** that does not exist.
- A **Customer** attempts to request delivery for an **Order** that already has one **Delivery Request**.
- A **Customer** submits a missing, incomplete, or unusable destination address.
- A **Customer** submits a requested delivery date that is earlier than the request date.
- A **Fulfillment Coordinator** attempts to review a **Delivery Request** that has already been approved or rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a **Customer** to submit a **Delivery Request** only for an existing **Order**.
- **FR-002**: The system MUST require each **Delivery Request** to belong to exactly one **Order**.
- **FR-003**: The system MUST allow each **Order** to be associated with zero or one **Delivery Request**.
- **FR-004**: The system MUST prevent a **Customer** from submitting more than one **Delivery Request** for the same **Order**.
- **FR-005**: The system MUST allow a **Customer** to submit zero or more instances of **Delivery Request** over time, provided each **Delivery Request** belongs to exactly one **Order**.
- **FR-006**: The system MUST require each **Delivery Request** to include a complete `destination_address` before submission.
- **FR-007**: The system MUST require each **Delivery Request** to include a `requested_delivery_date` before submission.
- **FR-008**: The system MUST prevent submission when a **Delivery Request** has a `requested_delivery_date` earlier than the date the request is made.
- **FR-009**: The system MUST assign a submitted **Delivery Request** an initial `status` of submitted until review is completed.
- **FR-010**: The system MUST allow a **Fulfillment Coordinator** to review zero or more instances of **Delivery Request**.
- **FR-011**: The system MUST allow a **Fulfillment Coordinator** to approve or reject a submitted **Delivery Request**.
- **FR-012**: The system MUST require a reviewed **Delivery Request** to be reviewed by exactly one **Fulfillment Coordinator**.
- **FR-013**: The system MUST preserve the original **Delivery Request** `destination_address` and `requested_delivery_date` after review.
- **FR-014**: The system MUST show authorized viewers whether an **Order** has zero or one **Delivery Request**, and when present show the **Delivery Request** `destination_address`, `requested_delivery_date`, and `status`.

### Key Entities *(include if feature involves data)*

- **Customer**: The existing domain actor previously modeled as the person or account that creates **Order** instances. In this feature, "client" requests are represented using **Customer**.
- **Order**: The existing customer purchase request that can be associated with zero or one **Delivery Request**.
- **Delivery Request**: A customer's request to deliver an existing **Order** to a `destination_address` on a `requested_delivery_date`; includes a review `status`.
- **Fulfillment Coordinator**: A fulfillment operations actor who reviews submitted **Delivery Request** instances and determines whether each request is approved or rejected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of customers can submit a valid delivery request for an eligible existing order in one attempt.
- **SC-002**: 100% of orders prevent more than one delivery request from being submitted for the same order.
- **SC-003**: Fulfillment coordinators can identify unreviewed delivery requests and record an approval or rejection outcome without needing information outside the request details.
- **SC-004**: 100% of delivery requests shown on order details display the same destination address, requested delivery date, and review status that were submitted or reviewed.

## Assumptions

- The existing **Customer** entity represents the prompt term "clients" because the prior order-management domain model uses **Customer** for the party that creates orders.
- A **Delivery Request** can only be created for an **Order** that already exists in the order-management domain.
- The feature introduces the new **Delivery Request** entity and the new **Fulfillment Coordinator** actor without changing existing **Order**, **Order Item**, or **Product** behavior outside delivery request visibility.
- A review outcome is limited to approved or rejected for this specification; scheduling, carrier assignment, delivery pricing, and delivery completion tracking are out of scope.
- Destination address completeness is evaluated as a business-valid delivery address, not merely non-empty text.
