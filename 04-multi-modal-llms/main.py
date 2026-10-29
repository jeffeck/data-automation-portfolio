import os
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import instructor
from openai import OpenAI
from anthropic import Anthropic

# =====================================================================
# 1. Pydantic Schemas for Strict Model Guardrails & Invariants
# =====================================================================

class ExtractedLineItem(BaseModel):
    description: str
    quantity: int = Field(gt=0, description="Quantity must be at least 1")
    unit_price: Decimal = Field(gt=0, description="Unit cost in USD")
    total_price: Decimal = Field(gt=0, description="Calculated line total")

    @field_validator("total_price")
    @classmethod
    def verify_line_total(cls, v: Decimal, info) -> Decimal:
        """Deterministic guardrail: Ensures the model didn't hallucinate line math."""
        values = info.data
        if "quantity" in values and "unit_price" in values:
            expected = Decimal(values["quantity"]) * values["unit_price"]
            if abs(v - expected) > Decimal("0.01"):
                raise ValueError(f"Line item math mismatch: {values['quantity']} * {values['unit_price']} != {v}")
        return v


class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_name: str
    tax_id: Optional[str] = None
    subtotal: Decimal = Field(gt=0)
    tax: Decimal = Field(ge=0)
    total_amount: Decimal = Field(gt=0)
    line_items: List[ExtractedLineItem]

    @field_validator("total_amount")
    @classmethod
    def verify_overall_sum(cls, v: Decimal, info) -> Decimal:
        """Deterministic balance check before payload leaves the extraction phase."""
        values = info.data
        if "subtotal" in values and "tax" in values:
            expected = values["subtotal"] + values["tax"]
            if abs(v - expected) > Decimal("0.01"):
                raise ValueError(f"Invoice total mismatch: {values['subtotal']} + {values['tax']} != {v}")
        return v


class ReconciliationReport(BaseModel):
    invoice_number: str
    po_matched: bool
    po_number: Optional[str]
    discrepancy_amount: Decimal
    discrepancy_type: Optional[str] = None  # e.g., "PRICE_VARIANCE", "LINE_COUNT_MISMATCH"
    requires_human_approval: bool
    raw_invoice_data: ExtractedInvoice


# =====================================================================
# 2. Stage 1 & 2: Local Preprocessing & SLM Extraction (Fast/Cheap)
# =====================================================================

def extract_invoice_with_slm(raw_text: str) -> ExtractedInvoice:
    """
    Uses a small, fast model (e.g., GPT-4o-mini or Gemini 2.5 Flash) via Instructor.
    Enforces the Pydantic schema and automatically retries if the model
    fails type casting or validator checks.
    """
    client = instructor.from_openai(OpenAI(api_key=os.environ.get("OPENAI_API_KEY")))
    
    # Notice: System prompt is focused purely on schema extraction, not strategy
    invoice: ExtractedInvoice = client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=ExtractedInvoice,
        max_retries=3,  # Instructor automatically feeds validation errors back to the model
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract structured invoice fields exactly as printed. "
                    "All numbers must be exact decimals. Do not extrapolate."
                ),
            },
            {"role": "user", "content": f"Invoice Text:\n{raw_text}"},
        ],
        temperature=0.0,
    )
    return invoice


# =====================================================================
# 3. Stage 3: Deterministic Verification & Database Fence (No LLM)
# =====================================================================

def reconcile_against_internal_db(invoice: ExtractedInvoice) -> ReconciliationReport:
    """
    PURE PYTHON / SQL STEP. No LLM tokens burned.
    Compares extracted data against internal Purchase Orders (POs) in the database.
    """
    # Simulated DB record from ERP / PostgreSQL
    mock_db_po = {
        "po_number": "PO-99481",
        "vendor_name": "Acme Industrial Logistics",
        "authorized_amount": Decimal("1500.00"),
        "max_variance_allowed": Decimal("50.00"),
    }

    # Deterministic variance check
    delta = invoice.total_amount - mock_db_po["authorized_amount"]
    
    if delta > mock_db_po["max_variance_allowed"]:
        return ReconciliationReport(
            invoice_number=invoice.invoice_number,
            po_matched=True,
            po_number=mock_db_po["po_number"],
            discrepancy_amount=delta,
            discrepancy_type="CRITICAL_OVERAGE_VARIANCE",
            requires_human_approval=True,
            raw_invoice_data=invoice,
        )

    return ReconciliationReport(
        invoice_number=invoice.invoice_number,
        po_matched=True,
        po_number=mock_db_po["po_number"],
        discrepancy_amount=delta,
        discrepancy_type=None,
        requires_human_approval=False,
        raw_invoice_data=invoice,
    )


# =====================================================================
# 4. Stage 4: Frontier LLM Strategic Executive Briefing (Deep Reasoning)
# =====================================================================

def generate_executive_briefing(reconciliation: ReconciliationReport) -> str:
    """
    Uses a Frontier Reasoning Model (e.g., Claude 3.5 Sonnet) ONLY on the 
    clean, pre-verified payload to evaluate strategic business impact.
    """
    anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Notice: We feed a compact, pre-validated summary, NOT the 20-page raw PDF text.
    context_payload = {
        "invoice_num": reconciliation.invoice_number,
        "vendor": reconciliation.raw_invoice_data.vendor_name,
        "authorized_budget": str(reconciliation.raw_invoice_data.total_amount - reconciliation.discrepancy_amount),
        "actual_billed": str(reconciliation.raw_invoice_data.total_amount),
        "variance": str(reconciliation.discrepancy_amount),
        "variance_flag": reconciliation.discrepancy_type,
        "flagged_for_human_review": reconciliation.requires_human_approval,
        "items": [item.model_dump(mode="json") for item in reconciliation.raw_invoice_data.line_items],
    }

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=600,
        temperature=0.2,
        system=(
            "You are a corporate finance intelligence assistant. Analyze the pre-verified "
            "invoice reconciliation data and write an executive briefing for the VP of Operations. "
            "Highlight budget variances, vendor contract compliance risks, and recommend concrete actions."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Verified Reconciliation Payload:\n{context_payload}",
            }
        ],
    )
    return response.content[0].text


# =====================================================================
# 5. Orchestration Pipeline (The DAG Runner)
# =====================================================================

def run_invoice_pipeline(raw_pdf_text: str):
    print("--- [STAGE 1 & 2] Extracting with SLM + Pydantic Guardrails ---")
    try:
        extracted = extract_invoice_with_slm(raw_pdf_text)
        print(f"Extracted Invoice #{extracted.invoice_number} from {extracted.vendor_name}")
        print(f"Total Billed: ${extracted.total_amount} (Validated: Subtotal + Tax matches Total)")
    except Exception as e:
        # Route to Dead-Letter Queue (DLQ) for manual audit
        print(f"[FATAL] Extraction schema failed validation: {e}")
        return

    print("\n--- [STAGE 3] Deterministic DB Reconciliation & Math Check ---")
    recon_result = reconcile_against_internal_db(extracted)
    print(f"PO Match: {recon_result.po_number} | Variance: ${recon_result.discrepancy_amount}")
    print(f"Requires Human Review: {recon_result.requires_human_approval}")

    print("\n--- [STAGE 4] Generating Strategic Executive Synthesis with Frontier Model ---")
    executive_memo = generate_executive_briefing(recon_result)
    print("Executive Memo Output:\n")
    print(executive_memo)


if __name__ == "__main__":
    # Simulated noisy text extracted via local PyMuPDF
    raw_document_input = """
    INVOICE #INV-2026-881
    Vendor: Acme Industrial Logistics
    Date: 2026-10-14
    
    Line Items:
    1. Premium Pallet Freight Handling (Qty: 2) @ $650.00 each -> $1300.00
    2. Emergency Fuel Surcharge (Qty: 1) @ $450.00 each -> $450.00
    
    Subtotal: $1750.00
    Tax (0%): $0.00
    TOTAL DUE: $1750.00
    """

    run_invoice_pipeline(raw_document_input)
