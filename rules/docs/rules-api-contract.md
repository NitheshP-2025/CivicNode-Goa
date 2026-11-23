
# CivicNode-Goa — Rules Service API Contract

## 1. Service Information

- Service: Rules and Calculator
- Base URL (local): http://127.0.0.1:8002
- Framework: FastAPI
- Port: 8002
- Authentication: Internal API key
- Header: X-Internal-Key

All endpoints except `/health` require internal authentication.

## 2. Health Check

### GET /health

Checks whether the Rules service is running.

Authentication: Not required.

## 3. Claim Evaluation

### POST /rules/evaluate

Evaluates claim evidence against the selected rule pack.

Authentication: Required.

Request:
- claim_id
- scheme
- incident_date
- rule_version (optional)
- facts

Response:
- claim_id
- scheme
- rule_pack
- conditions
- overall_status
- notices

The service identifies conditions requiring officer review.
It does not make final claim approval decisions.

## 4. Compensation Calculation

### POST /calc

Performs deterministic compensation calculations.

Authentication: Required.

Supported schemes:
- flood_relief
- land_acquisition

Request example — flood relief:

{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "flood_relief": {
    "eligible_area": {
      "value": "2",
      "unit": "hectare"
    }
  }
}

Important:
- Rates are loaded from the selected rule pack.
- The client must not supply compensation rates.
- Decimal monetary and area values must be sent as strings where required by the schema.
- Results include the rule-pack version and SHA-256 hash.
- Demo calculations are not official compensation assessments.

## 5. Generate PDF Receipt

### POST /receipts/pdf

Creates, stores and returns a downloadable PDF receipt.

Authentication: Required.

Request:
The completed calculation response fields:
- claim_id
- scheme
- incident_date
- rule_pack
- calculation
- notices (optional)

Response:
- Content-Type: application/pdf
- Content-Disposition: attachment

The generated receipt includes:
- Unique receipt ID
- Claim ID
- Scheme and incident date
- Rule-pack version and status
- Calculation summary
- Disclaimers and officer-review status

## 6. Retrieve Receipt

### GET /receipts/{receipt_id}

Retrieves a stored receipt as JSON.

Authentication: Required.

Possible responses:
- 200: Receipt found
- 404: Receipt not found

## 7. Download Existing Receipt

### GET /receipts/{receipt_id}/pdf

Generates a PDF from a previously stored receipt.

Authentication: Required.

Possible responses:
- 200: PDF returned
- 404: Receipt not found

This operation does not create another receipt.

## 8. Verify Audit Trail

### GET /audit/verify

Checks the integrity of the SHA-256 audit chain.

Authentication: Required.

Response fields:
- service
- audit_integrity
- valid
- entries_checked
- error
- last_hash

A valid result indicates that the checked records form a consistent hash chain.

## 9. Error Handling

Common HTTP responses:

| Status | Meaning |
|---|---|
| 200 | Successful request |
| 401 | Internal key missing |
| 403 | Invalid internal key |
| 404 | Resource not found |
| 422 | Request validation or processing error |
| 503 | Authentication configuration unavailable |

## 10. Integration Responsibilities

Backend service:
- Collect claim information.
- Coordinate document, registry and flood evidence services.
- Send validated calculation requests.
- Store and manage claim workflow status.
- Present results to authorised officers.

Rules service:
- Load versioned rule packs.
- Evaluate evidence conditions.
- Calculate compensation deterministically.
- Generate and store receipts.
- Maintain and verify its audit chain.

Final compensation decisions remain with authorised officers.

## 11. Important Constraints

- AI recommendations do not constitute approval.
- Synthetic demo rates are not official government rates.
- Satellite flood evidence is supporting evidence, not proof of crop damage.
- Every calculation must remain traceable to its rule-pack version and inputs.
- Receipt generation does not authorise payment.
