#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOLS_DIR="$ROOT_DIR/spec-kit/spec-kit-domain-minimal"

HAS_DOCX=0
if python3 -c "import docx" >/dev/null 2>&1; then
  HAS_DOCX=1
fi

if [ "$HAS_DOCX" -eq 0 ]; then
  echo "python-docx is not installed. Regenerating Markdown report only."
  echo "Install it with: python3 -m pip install python-docx"
fi

python3 "$TOOLS_DIR/extract_domain_model.py" \
  specs/001-order-management/spec.md \
  -o specs/001-order-management/feature-domain.json

python3 "$TOOLS_DIR/extract_domain_model.py" \
  specs/002-delivery-requests/spec.md \
  -o specs/002-delivery-requests/feature-domain.json

if [ "$HAS_DOCX" -eq 1 ]; then
  python3 "$TOOLS_DIR/check_domain_evolution.py" \
    --base specs/001-order-management/feature-domain.json \
    --next specs/002-delivery-requests/feature-domain.json \
    --rationale specs/002-delivery-requests/domain-rationale.json \
    --out-md specs/002-delivery-requests/domain-evolution-report.md \
    --out-docx specs/002-delivery-requests/domain-evolution-report.docx
else
  python3 "$TOOLS_DIR/check_domain_evolution.py" \
    --base specs/001-order-management/feature-domain.json \
    --next specs/002-delivery-requests/feature-domain.json \
    --rationale specs/002-delivery-requests/domain-rationale.json \
    --out-md specs/002-delivery-requests/domain-evolution-report.md
fi

python3 "$TOOLS_DIR/generate_domain_delta.py" \
  --base specs/001-order-management/feature-domain.json \
  --next specs/002-delivery-requests/feature-domain.json \
  --rationale specs/002-delivery-requests/domain-rationale.json \
  -o specs/002-delivery-requests/domain-delta.json >/dev/null

python3 "$TOOLS_DIR/merge_domain_delta.py" \
  --base specs/001-order-management/feature-domain.json \
  --delta specs/002-delivery-requests/domain-delta.json \
  -o specs/shared-domain-model.json >/dev/null

echo "Regenerated domain artifacts under examples/order-delivery/specs"
