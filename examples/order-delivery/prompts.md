# Example Prompts

## Feature 1

```text
$speckit-specify SPECIFY_FEATURE_DIRECTORY=specs/001-order-management Build an order management feature where customers can create orders containing order items, each order item references a product, and each order belongs to exactly one customer.
```

## Feature 2

```text
$speckit-specify SPECIFY_FEATURE_DIRECTORY=specs/002-delivery-requests Read and use the existing domain model at specs/001-order-management/feature-domain.json as prior domain context. Add delivery requests where clients can request delivery for an existing order, each order can have zero or one delivery request, fulfillment coordinators can review delivery requests, and delivery requests include a destination address and requested delivery date.
```

