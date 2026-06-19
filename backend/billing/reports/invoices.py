# billing/reports/invoices.py
from __future__ import annotations

from typing import Any

from billing.invoices import Invoice, InvoiceStatus
from monitoring.logging import get_logger

logger = get_logger("neuralcore.billing.reports.invoices")


async def get_outstanding_invoices(db: Any, organization_id: str | None = None) -> dict[str, Any]:
    return {"organization_id": organization_id, "outstanding_count": 0, "outstanding_total_usd": 0.0, "invoices": []}


async def get_invoice_summary(db: Any, range_str: str = "30d") -> dict[str, Any]:
    return {
        "range": range_str,
        "total_invoices": 0,
        "total_paid_usd": 0.0,
        "total_outstanding_usd": 0.0,
        "total_overdue_usd": 0.0,
        "by_status": {status.value: 0 for status in InvoiceStatus},
    }


def export_invoice_as_pdf_data(invoice: Invoice, organization_name: str, billing_address: str = "") -> dict[str, Any]:
    return {
        "invoice_number": invoice.invoice_number,
        "organization_name": organization_name,
        "billing_address": billing_address,
        "issued_at": invoice.issued_at,
        "due_at": invoice.due_at,
        "line_items": [item.to_dict() for item in invoice.line_items],
        "subtotal": invoice.subtotal,
        "tax_amount": invoice.tax_amount,
        "total": invoice.total,
        "currency": invoice.currency,
        "status": invoice.status.value,
    }
