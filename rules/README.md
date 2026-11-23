# CivicNode-Goa — Rules & Calculator Microservice

The Rules & Calculator microservice is a deterministic compensation calculation, claim evidence evaluation, and verifiable audit service for the CivicNode-Goa platform.

It is responsible for:
- Evaluating claim facts and evidence conditions against versioned rule packs.
- Computing deterministic compensation calculations using Python's `Decimal` arithmetic.
- Dynamic loading, version selection, and SHA-256 cryptographic verification of YAML rule packs.
- Generating verifiable, downloadable PDF receipts using ReportLab.
- Persisting receipts and maintaining a tamper-evident SHA-256 hash-chained audit trail in SQLite.
- Verifying the integrity of the audit hash chain.

---

> [!IMPORTANT]
> **DEMONSTRATION DISCLAIMER**: All current compensation rates (e.g., ₹1,111.11/hectare for flood relief, 10% solatium, and 5% interest for land acquisition), eligibility rules, and calculation formulas in this service are **synthetic demonstration values**. They do NOT represent official Government of Goa policies, statutory compensation orders, or gazetted rates.
>
> **OFFICER DISCRETION**: AI recommendations and automated rule evaluations are advisory. Final compensation determinations and claim approvals remain the sole responsibility of authorised government officers.

---

## Architecture Overview

The microservice is built using **Python 3.11** and **FastAPI**, operating as an isolated internal microservice on port **8002**.

```
                           +------------------------+
                           |  CivicNode Core / API  |
                           +-----------+------------+
                                       |
                   HTTP + X-Internal-Key Header (Port 8002)
                                       |
                                       v
+--------------------------------------------------------------------------+
| Rules Microservice                                                       |
|                                                                          |
|  +--------------------+   +-----------------------+   +---------------+  |
|  |   FastAPI Layer    |-->|  Pydantic V2 Schemas  |-->| Security Auth |  |
|  |     (api.py)       |   |     (schemas.py)      |   | (security.py) |  |
|  +---------+----------+   +-----------------------+   +---------------+  |
|            |                                                             |
|            +-----------------------+-----------------------+             |
|            |                       |                       |             |
|            v                       v                       v             |
|  +--------------------+  +--------------------+  +--------------------+  |
|  |   Rule Engine      |  |    Calculators     |  | Receipt & Audit    |  |
|  | - loader.py (YAML) |  | - flood_relief.py  |  | - builder.py       |  |
|  | - evaluate.py      |  | - land_acq.py      |  | - pdf_generator.py |  |
|  | - SHA-256 pack hash|  | - rounding.py (Dec)|  | - audit_chain.py   |  |
|  +---------+----------+  +--------------------+  | - storage.py       |  |
|            |                                     +---------+----------+  |
|            v                                               |             |
|      YAML Packs                                      SQLite Storage      |
|    (rules/packs/)                                (rules/data/audit.db)   |
+--------------------------------------------------------------------------+
```

Key Architectural Principles:
1. **Deterministic Arithmetic**: Financial calculations strictly use `decimal.Decimal` and `ROUND_HALF_UP` quantization to two decimal places (`0.01`). Floating-point types are rejected at the schema level.
2. **Strict Request Models**: All incoming request schemas extend `StrictModel` (`ConfigDict(extra="forbid")`), preventing unexpected payloads.
3. **Fail-Closed Security**: When `RULES_INTERNAL_KEY` is not configured, the service returns HTTP 503 rather than operating insecurely. Secret comparison uses constant-time matching (`secrets.compare_digest`).
4. **Atomic Audit Persistence**: Receipt persistence and audit trail logging execute within a single SQLite transaction (`BEGIN IMMEDIATE`), ensuring both succeed or both roll back together.

---

## Directory Structure

```
rules/
├── api.py                    # FastAPI application, route definitions, error handlers
├── config.py                 # Configuration dataclass and environment variable loader
├── errors.py                 # Custom exception hierarchy (RulesServiceError)
├── requirements.txt          # Python runtime and testing dependencies
├── schemas.py                # Pydantic V2 request/response models with strict validation
├── security.py               # Internal API key header verification dependency
├── service.py                # Service orchestration for calculation and audit logging
├── README.md                 # Microservice documentation (this file)
├── calculator/
│   ├── __init__.py
│   ├── flood_relief.py       # Flood relief arithmetic and unit conversion
│   ├── land_acquisition.py   # Land acquisition valuation (land, structures, trees, solatium, interest)
│   └── rounding.py           # Decimal conversion, INR formatting, and ROUND_HALF_UP rounding
├── data/
│   └── audit.db              # SQLite database storing receipts and SHA-256 audit chain
├── docs/
│   └── rules-api-contract.md # API specification and contract documentation
├── engine/
│   ├── __init__.py
│   ├── evaluate.py           # Claim facts and evidence conditions evaluation logic
│   └── loader.py             # YAML rule pack loading, date matching, and SHA-256 hashing
├── packs/
│   ├── flood_relief_v1.yaml      # Demonstration flood relief rule pack
│   └── land_acquisition_v1.yaml  # Demonstration land acquisition rule pack
├── receipts/
│   ├── __init__.py
│   ├── audit_chain.py        # Cryptographic SHA-256 audit chain and verification
│   ├── builder.py            # Receipt construction with disclaimers and traceability
│   ├── pdf_generator.py      # ReportLab PDF receipt generator
│   └── storage.py            # SQLite storage operations and atomic save transactions
└── tests/                    # Pytest test suite (149 automated test cases)
```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv`)

### 1. Create and Activate Virtual Environment
```bash
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r rules/requirements.txt
```

### 3. Run the Microservice
```bash
# Set internal secret key (required for authenticated endpoints):
$env:RULES_INTERNAL_KEY="your-internal-secret-key"

# Launch using Uvicorn:
uvicorn rules.api:app --host 127.0.0.1 --port 8002 --reload
```

---

## Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `RULES_HOST` | String | `127.0.0.1` | Network interface to bind to. |
| `RULES_PORT` | Integer | `8002` | Port on which the service listens. |
| `RULES_ENV` | String | `development` | Operating environment (`development`, `production`). |
| `RULES_INTERNAL_KEY` | String | `None` | Shared secret key for internal service-to-service authentication. If unset, protected endpoints return HTTP 503. |
| `RULES_DATABASE_PATH` | Path | `rules/data/audit.db` | Absolute or relative path to the SQLite audit database. |

---

## Authentication

All endpoints except `GET /health` require the `X-Internal-Key` HTTP header.

```http
X-Internal-Key: <your-configured-key>
```

- **Missing Header**: HTTP `401 Unauthorized` with header `WWW-Authenticate: ApiKey`.
- **Invalid Key**: HTTP `403 Forbidden` (`{"code": "INVALID_INTERNAL_KEY", "message": "The supplied internal API key is invalid."}`).
- **Key Unset on Server**: HTTP `503 Service Unavailable` (`{"code": "AUTH_NOT_CONFIGURED", "message": "Internal API authentication is not configured."}`).

---

## API Endpoints & Examples

### 1. Health Check
Checks service availability. No authentication required.

- **URL**: `GET /health`
- **Response** (HTTP 200):
```json
{
  "service": "rules",
  "status": "healthy",
  "port": 8002
}
```

---

### 2. Claim Evaluation
Evaluates claim facts against rule pack conditions. Flags conditions requiring officer review.

- **URL**: `POST /rules/evaluate`
- **Headers**: `X-Internal-Key: <secret>`, `Content-Type: application/json`
- **Request Body**:
```json
{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "rule_version": "v1",
  "facts": {
    "survey_number": "SUR-101",
    "eligible_area": {
      "value": "1.2500",
      "unit": "hectare"
    },
    "registry_match": true,
    "flood_evidence": {
      "status": "flooded",
      "overlap_percent": "75.50"
    },
    "duplicate_status": "clear",
    "documents_verified": true
  }
}
```
- **Response** (HTTP 200):
```json
{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "overall_status": "review_required",
  "conditions": [
    {
      "rule_id": "DOC-001",
      "title": "Document verification",
      "status": "passed",
      "reason": "Documents are marked as verified by the upstream workflow.",
      "clause": null,
      "source_document": null,
      "inputs_used": { "documents_verified": true }
    },
    {
      "rule_id": "REG-001",
      "title": "Land registry matching",
      "status": "passed",
      "reason": "The upstream registry check reports a match.",
      "clause": null,
      "source_document": null,
      "inputs_used": { "registry_match": true }
    },
    {
      "rule_id": "DUP-001",
      "title": "Duplicate claim screening",
      "status": "passed",
      "reason": "The upstream duplicate screening reports no duplicate.",
      "clause": null,
      "source_document": null,
      "inputs_used": { "duplicate_status": "clear" }
    },
    {
      "rule_id": "FLD-001",
      "title": "Flood evidence availability",
      "status": "passed",
      "reason": "Flood evidence was supplied. It is supporting evidence, not proof of crop damage or eligibility.",
      "clause": null,
      "source_document": null,
      "inputs_used": { "status": "flooded", "overlap_percent": "75.50" }
    },
    {
      "rule_id": "AREA-001",
      "title": "Eligible land area availability",
      "status": "passed",
      "reason": "Eligible land area was supplied by the upstream workflow.",
      "clause": null,
      "source_document": null,
      "inputs_used": { "value": "1.2500", "unit": "hectare" }
    }
  ],
  "rule_pack": {
    "scheme": "flood_relief",
    "version": "v1",
    "status": "demo",
    "sha256": "43924fca53dbecce126ecfbf4c64379ba5184285be292a838be28ce26bdf3b92"
  },
  "notices": [
    "DEMO RULE PACK: No official eligibility determination or government compensation policy is implemented.",
    "AI-assisted evidence screening does not replace the authorised officer's decision."
  ]
}
```

---

### 3. Compensation Calculation
Performs deterministic calculations using parameters loaded from the versioned rule pack.

- **URL**: `POST /calc`
- **Headers**: `X-Internal-Key: <secret>`, `Content-Type: application/json`

#### Example A: Flood Relief
- **Request Body**:
```json
{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "flood_relief": {
    "eligible_area": {
      "value": "2.0000",
      "unit": "hectare"
    }
  }
}
```
- **Response** (HTTP 200):
```json
{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "rule_pack": {
    "version": "v1",
    "status": "demo",
    "sha256": "43924fca53dbecce126ecfbf4c64379ba5184285be292a838be28ce26bdf3b92"
  },
  "calculation": {
    "scheme": "flood_relief",
    "eligible_area": {
      "value": "2.0000",
      "unit": "hectare"
    },
    "normalized_area_hectares": "2.0000",
    "rate_per_hectare": "1111.11",
    "formula": "eligible_area_hectares * rate_per_hectare",
    "raw_amount": "2222.220000",
    "total": "2222.22",
    "currency": "INR",
    "rounding": "ROUND_HALF_UP",
    "notices": [
      "DEMO CALCULATION: Synthetic rate used.",
      "This calculation is not an official Government of Goa compensation determination."
    ]
  },
  "notices": [
    "DEMO CALCULATION: Synthetic rate used.",
    "This calculation is not an official Government of Goa compensation determination.",
    "This calculation uses a synthetic demonstration rule pack. It is not an official Government of Goa compensation assessment.",
    "This calculation requires authorised officer review."
  ]
}
```

#### Example B: Land Acquisition
- **Request Body**:
```json
{
  "claim_id": "CLM-LAND-001",
  "scheme": "land_acquisition",
  "incident_date": "2026-06-15",
  "land_acquisition": {
    "land_value": "100000.00",
    "structures": [
      { "description": "Residential House", "value": "20000.00" },
      { "description": "Boundary Wall", "value": "5000.00" }
    ],
    "trees": [
      { "description": "Coconut Palm", "value": "3000.00" }
    ],
    "interest_start_date": "2026-01-01",
    "interest_end_date": "2027-01-01"
  }
}
```
- **Response** (HTTP 200):
```json
{
  "claim_id": "CLM-LAND-001",
  "scheme": "land_acquisition",
  "incident_date": "2026-06-15",
  "rule_pack": {
    "version": "v1",
    "status": "demo",
    "sha256": "4ba98b0463c631c3bf1e03a93a54b3ee4a621be137837016cf1f40d82d499ae1"
  },
  "calculation": {
    "scheme": "land_acquisition",
    "currency": "INR",
    "line_items": [
      { "component": "land", "amount": "100000.00" },
      {
        "component": "structures",
        "amount": "25000.00",
        "items": [
          { "description": "Residential House", "value": "20000.00" },
          { "description": "Boundary Wall", "value": "5000.00" }
        ]
      },
      {
        "component": "trees",
        "amount": "3000.00",
        "items": [
          { "description": "Coconut Palm", "value": "3000.00" }
        ]
      },
      { "component": "solatium", "rate": "0.10", "amount": "12800.00" },
      {
        "component": "interest",
        "annual_rate": "0.05",
        "principal": "140800.00",
        "days": 365,
        "basis_days": 365,
        "amount": "7040.00"
      }
    ],
    "formula": "land + structures + trees + solatium + simple_interest",
    "base_value": "128000.00",
    "total_before_rounding": "147840.0000",
    "total": "147840.00",
    "rounding": "ROUND_HALF_UP",
    "notices": [
      "DEMO CALCULATION: All rates and formulas are illustrative.",
      "Not an official Government of Goa compensation determination.",
      "Interest and solatium methodology must be verified against applicable legal provisions before production use."
    ]
  },
  "notices": [
    "DEMO CALCULATION: All rates and formulas are illustrative.",
    "Not an official Government of Goa compensation determination.",
    "Interest and solatium methodology must be verified against applicable legal provisions before production use.",
    "This calculation uses a synthetic demonstration rule pack. It is not an official Government of Goa compensation assessment.",
    "This calculation requires authorised officer review."
  ]
}
```

---

### 4. Generate & Download Receipt PDF
Builds a persistent receipt, commits it and an audit event atomically to SQLite, and returns the rendered PDF.

- **URL**: `POST /receipts/pdf`
- **Headers**: `X-Internal-Key: <secret>`, `Content-Type: application/json`
- **Request Body**:
```json
{
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "rule_pack": {
    "version": "v1",
    "status": "demo",
    "sha256": "43924fca53dbecce126ecfbf4c64379ba5184285be292a838be28ce26bdf3b92"
  },
  "calculation": {
    "formula": "eligible_area_hectares * rate_per_hectare",
    "total": "2222.22",
    "currency": "INR",
    "rounding": "ROUND_HALF_UP"
  },
  "notices": ["Synthetic demonstration calculation."]
}
```
- **Response** (HTTP 200):
  - **Content-Type**: `application/pdf`
  - **Content-Disposition**: `attachment; filename="RCP-XXXXXXXXXXXX.pdf"`

---

### 5. Retrieve Stored Receipt (JSON)
Retrieves a previously stored receipt by ID.

- **URL**: `GET /receipts/{receipt_id}`
- **Headers**: `X-Internal-Key: <secret>`
- **Response** (HTTP 200):
```json
{
  "receipt_id": "RCP-A1B2C3D4E5F6",
  "created_at": "2026-11-23T12:00:00Z",
  "generated_at": "2026-11-23T12:00:00Z",
  "claim_id": "CLM-FLOOD-001",
  "scheme": "flood_relief",
  "incident_date": "2026-06-15",
  "receipt_status": "demonstration",
  "decision_status": "pending_officer_review",
  "rule_pack": {
    "version": "v1",
    "status": "demo",
    "sha256": "43924fca53dbecce126ecfbf4c64379ba5184285be292a838be28ce26bdf3b92"
  },
  "calculation": {
    "formula": "eligible_area_hectares * rate_per_hectare",
    "total": "2222.22",
    "currency": "INR",
    "rounding": "ROUND_HALF_UP"
  },
  "notices": [
    "Synthetic demonstration calculation.",
    "This receipt documents a synthetic demonstration calculation. It is not an official Government of Goa compensation order or proof of payment.",
    "The calculation is advisory and requires authorised officer review."
  ]
}
```
- **If Not Found**: HTTP `404 Not Found` (`{"detail": "Receipt not found"}`).

---

### 6. Download Existing Receipt PDF
Regenerates and streams a PDF for an existing stored receipt without creating duplicate database records.

- **URL**: `GET /receipts/{receipt_id}/pdf`
- **Headers**: `X-Internal-Key: <secret>`
- **Response** (HTTP 200):
  - **Content-Type**: `application/pdf`
  - **Content-Disposition**: `attachment; filename="RCP-A1B2C3D4E5F6.pdf"`

---

### 7. Verify Audit Hash Chain
Traverses the SQLite audit trail from genesis to the latest record, verifying entry hashes and cryptographic link pointers.

- **URL**: `GET /audit/verify`
- **Headers**: `X-Internal-Key: <secret>`
- **Response** (HTTP 200 - Valid Chain):
```json
{
  "service": "rules",
  "audit_integrity": "valid",
  "valid": true,
  "entries_checked": 34,
  "error": null,
  "last_hash": "a1b2c3d4e5f6...64hex"
}
```
- **Response** (HTTP 200 - Tampered Chain):
```json
{
  "service": "rules",
  "audit_integrity": "compromised",
  "valid": false,
  "entries_checked": 12,
  "error": "Entry hash mismatch at entry 13",
  "last_hash": "..."
}
```

---

## Rule-Pack Configuration & Versioning

Rule packs are defined in YAML files under `rules/packs/` following the naming convention `<scheme>_<version>.yaml` (e.g., `flood_relief_v1.yaml`).

### Schema Definition
```yaml
scheme: flood_relief                 # Must be 'flood_relief' or 'land_acquisition'
version: v1                          # Alphanumeric version identifier
status: demo                         # 'demo' or 'verified'

effective_from: "2026-01-01"         # ISO-8601 start date
effective_to: null                   # ISO-8601 end date (or null if currently active)

description: >
  Synthetic demonstration rule pack.
  Not an official Government of Goa compensation policy.

source_documents: []                 # List of statutory citations or gazette references

calculation:
  method: area_times_rate_per_hectare
  rate_per_hectare: "1111.11"        # Decimal string
  rate_status: demo

rules: []
```

### Version Selection Rules:
1. **Explicit Version**: If `rule_version` is supplied in the request, that specific pack is loaded. The claim's `incident_date` is validated to ensure it falls within `[effective_from, effective_to]`. If outside the range, HTTP `422 RULE_VERSION_NOT_EFFECTIVE` is raised.
2. **Automatic Selection**: If `rule_version` is omitted, the loader scans all packs matching `scheme_*.yaml` and selects the pack effective on `incident_date`. If multiple packs match, HTTP `409 AMBIGUOUS_RULE_VERSION` is raised. If none match, HTTP `404 RULE_PACK_NOT_FOUND` is raised.
3. **Deterministic Pack Hash**: Each pack is assigned a SHA-256 hash computed over canonical JSON (dates serialized to ISO strings, keys sorted, compact delimiters).

---

## Calculation Explanations

### 1. Flood Relief
- **Normalized Area**: Input area is converted to hectares:
  $$\text{area}_{\text{ha}} = \frac{\text{area} \times \text{conversion\_factor}}{10000}$$
  - $1 \text{ hectare} = 10,000 \text{ sq m}$
  - $1 \text{ are} = 100 \text{ sq m}$
  - $1 \text{ sq m} = 1 \text{ sq m}$
- **Compensation Formula**:
  $$\text{Compensation} = \text{Normalized Area (hectares)} \times \text{Rate per Hectare}$$
- **Rounding**: Quantized to 2 decimal places using `ROUND_HALF_UP`.

### 2. Land Acquisition
- **Base Value**: Sum of land valuation and non-negative line items:
  $$\text{Base Value} = \text{Land Value} + \sum \text{Structures} + \sum \text{Trees}$$
- **Solatium**: Solatium allowance (percentage bounded in $[0, 1]$):
  $$\text{Solatium} = \text{Base Value} \times \text{Solatium Rate}$$
- **Interest**: Simple interest on total principal over elapsed days:
  $$\text{Principal} = \text{Base Value} + \text{Solatium}$$
  $$\text{Interest} = \text{Principal} \times \text{Annual Interest Rate} \times \frac{\text{End Date} - \text{Start Date}}{\text{Basis Days}}$$
- **Total Compensation**:
  $$\text{Total} = \text{Round}(\text{Base Value} + \text{Solatium} + \text{Interest})$$

---

## Receipt & Audit Lifecycle

```
  POST /calc / receipts/pdf
             │
             ▼
  ┌──────────────────────┐
  │  build_receipt()     │ ──> Assigns unique RCP-XXXXXXXXXXXX ID, timestamps, disclaimers
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ generate_receipt_pdf │ ──> Builds ReportLab Flowable document in memory
  └──────────┬───────────┘
             │
             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ save_receipt_with_audit()                                   │
  │                                                             │
  │   BEGIN IMMEDIATE                                           │
  │     ├── INSERT INTO receipts (receipt_id, json, ...)        │
  │     └── append_audit_event_in_transaction()                 │
  │           ├── Fetch previous entry_hash (or GENESIS_HASH)   │
  │           ├── Compute entry_hash = SHA256(canonical_json)   │
  │           └── INSERT INTO audit_entries (...)               │
  │   COMMIT (or ROLLBACK on any error)                         │
  └─────────────────────────────────────────────────────────────┘
```

- **Genesis Hash**: The initial entry is linked to `0000000000000000000000000000000000000000000000000000000000000000` (64 zeros).
- **Entry Hash Calculation**:
  $$\text{Entry Hash} = \text{SHA256}(\text{CanonicalJSON}(\{\text{event\_type}, \text{entity\_id}, \text{payload\_json}, \text{created\_at}, \text{previous\_hash}\}))$$

---

## Testing

Run the full automated test suite using `pytest`:

```bash
# Execute complete test suite:
python -m pytest rules/tests/ -v

# Run a specific test suite:
python -m pytest rules/tests/test_evaluate.py -v

# Run with warnings displayed:
python -m pytest rules/tests/ -v -W default
```

Current test baseline: **149 passed, 1 warning** (from upstream Starlette multipart deprecation).

---

## Known Limitations

1. **Unanchored Hash Chain Tail Deletion**:
   The internal SHA-256 hash chain links each record to its predecessor. Tampering with any historical entry or deleting any record between the genesis block and the tail is cryptographically detected by `GET /audit/verify`. However, **an unanchored hash chain cannot independently detect the silent deletion of its final entry ($N$)**, because the truncated chain ($1 \dots N-1$) remains mathematically self-consistent. To achieve non-repudiation against tail truncation, the service requires an external anchoring mechanism (e.g., publishing `last_hash` periodic checkpoints to an external ledger, digital timestamp authority, or immutable external log).
2. **Single SQLite Instance Deployment**:
   Database concurrency is managed via SQLite's write-ahead log and `BEGIN IMMEDIATE` transactions with a 10-second busy timeout. This is designed for single-node microservice deployment. Running multi-replica horizontal instances against a shared network filesystem is unsupported without migrating the audit storage layer to PostgreSQL or distributed ledger storage.
3. **Synthetic Demonstration Rates**:
   All rates, compensation amounts, and solatium/interest ratios are illustrative demonstration values. They must be updated with verified gazetted rules before any production legal deployment.
4. **Advisory Decision Status**:
   All evaluation conditions and receipts flag claims as `review_required` / `pending_officer_review`. The microservice does not perform autonomous legal claim approval.
