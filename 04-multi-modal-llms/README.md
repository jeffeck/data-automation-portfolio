# Multi-Model Invoice Intelligence Pipeline

A resilient, cost-optimized document intelligence DAG (Directed Acyclic Graph) built in Python. This pipeline automates the extraction, verification, internal database reconciliation, and executive briefing generation for vendor invoices and receipts.

Rather than delegating the entire workflow to a single, expensive frontier reasoning model, the architecture partitions tasks across **deterministic tools**, **compact extraction models (SLMs)**, and **frontier reasoning models (LLMs)** based on cost, latency, and failure tolerance.

---

## Architecture Overview

```text
[ Raw Document Text ]
         │
         ▼
[ Stage 1 & 2: Structural Extraction ]
  • Model: Small Language Model (e.g., GPT-4o-mini / Gemini 2.5 Flash) via `instructor`
  • Enforcement: Pydantic schemas with strict runtime validators
  • Scope: Text-to-JSON mapping; mathematical sanity checks
         │
         ▼ (Validated ExtractedInvoice Payload)
[ Stage 3: Deterministic Reconciliation & Fence ]
  • Engine: Pure Python / SQL (No AI)
  • Logic: Decimal precision delta checks against ERP / DB Purchase Orders
  • Output: ReconciliationReport with explicit human-in-the-loop flags
         │
         ▼ (Compact Context: < 300 Tokens)
[ Stage 4: Strategic Synthesis & Executive Briefing ]
  • Model: Frontier Reasoning Model (e.g., Claude 3.5 Sonnet / GPT-4o)
  • Scope: Anomaly analysis, contract compliance evaluation, executive memo
```

---

## Core Design Principles

1. **Deterministic Isolation for Business Logic & Math:**  
   LLMs are probabilistic and prone to arithmetic hallucinations. Line-item totals, subtotal additions, and database budget variances are computed exclusively using Python's `Decimal` type and strict Pydantic field validators.

2. **Asymmetric Model Routing (Token Economics):**  
   - **SLM (Extraction):** Runs at approximately 1/15th the token cost of a flagship model. It handles entity extraction and format normalization under `temperature=0.0`.
   - **Frontier LLM (Synthesis):** Never sees multi-page noisy OCR text. It is invoked only at the final step with a pre-validated, pre-reconciled JSON payload, keeping prompt token volume minimal and response times fast.

3. **Self-Healing Schemas & Dead-Letter Isolation:**  
   The extraction layer leverages `instructor` retries. If the SLM produces a schema violation or fails a `@field_validator` math constraint, the validation traceback is fed back to the model for automated correction (up to 3 attempts) before failing over to an operational Dead-Letter Queue (DLQ).

---

## Prerequisites

- **Python:** 3.10+
- **API Keys:**
  - `OPENAI_API_KEY` (used for the fast extraction tier via `gpt-4o-mini`)
  - `ANTHROPIC_API_KEY` (used for the strategic briefing tier via `claude-3-5-sonnet-20241022`)

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/invoice-intel-pipeline.git
   cd invoice-intel-pipeline
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install pydantic instructor openai anthropic
   ```

---

## Environment Configuration

Export the required API keys to your environment:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

---

## Running the Pipeline

Execute the script directly to process the sample document text:

```bash
python invoice_pipeline.py
```

### Expected Output Flow

```text
--- [STAGE 1 & 2] Extracting with SLM + Pydantic Guardrails ---
Extracted Invoice #INV-2026-881 from Acme Industrial Logistics
Total Billed: $1750.00 (Validated: Subtotal + Tax matches Total)

--- [STAGE 3] Deterministic DB Reconciliation & Math Check ---
PO Match: PO-99481 | Variance: $250.00
Requires Human Review: True

--- [STAGE 4] Generating Strategic Executive Synthesis with Frontier Model ---
Executive Memo Output:

MEMORANDUM

TO: Vice President of Operations
FROM: Finance Intelligence Automation
DATE: October 28, 2026
SUBJECT: Variance & Compliance Alert: Acme Industrial Logistics (Invoice #INV-2026-881)

1. Executive Summary
Invoice #INV-2026-881 submitted by Acme Industrial Logistics reflects total billing of $1,750.00 against authorized PO-99481 ($1,500.00), creating an unauthorized budget overage of $250.00 (+16.7%). This exceeds our automated variance threshold ($50.00) and has been placed on administrative hold.

2. Cost Driver Analysis
- Line 1: Premium Pallet Freight Handling (2 units @ $650.00 = $1,300.00) aligns with base service expectations.
- Line 2: Emergency Fuel Surcharge (1 unit @ $450.00 = $450.00) represents the entirety of the variance.

3. Recommended Actions
- Withhold payment approval pending verification of emergency logistics authorization.
- Request documentation from procurement regarding contracted caps on fuel surcharges for Q4 2026.
```

---

## Data Contracts (Pydantic Schemas)

### `ExtractedInvoice`
Guarantees the raw extracted document satisfies data integrity invariants before passing down the DAG:
- `subtotal` + `tax` == `total_amount` (within $\pm\$0.01$)
- `quantity` $\times$ `unit_price` == `total_price` for each line item
- Quantities strictly $> 0$; costs strictly $\ge 0$

### `ReconciliationReport`
The audit manifest passed between deterministic ERP systems and the downstream frontier model:
- `po_matched`: Boolean match status against internal records
- `discrepancy_amount`: Signed numeric variance
- `requires_human_approval`: Triggers approval workflows when variance exceeds authorized tolerances

---

## License

Apache 2.0. See `LICENSE` for details.
