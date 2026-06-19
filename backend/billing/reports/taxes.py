# billing/reports/taxes.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_DEFAULT_TAX_RATES: dict[str, float] = {
    "US": 0.0,
    "IN": 0.18,
    "GB": 0.20,
    "DE": 0.19,
    "FR": 0.20,
    "CA": 0.05,
    "AU": 0.10,
    "SG": 0.09,
    "AE": 0.05,
}


@dataclass(slots=True, frozen=True)
class TaxCalculation:
    country_code: str
    tax_rate: float
    taxable_amount: float
    tax_amount: float
    tax_name: str

    def to_dict(self) -> dict[str, Any]:
        return {"country_code": self.country_code, "tax_rate": self.tax_rate, "taxable_amount": self.taxable_amount, "tax_amount": self.tax_amount, "tax_name": self.tax_name}


_TAX_NAMES: dict[str, str] = {"IN": "GST", "GB": "VAT", "DE": "VAT", "FR": "VAT", "AU": "GST", "CA": "GST", "SG": "GST", "AE": "VAT", "US": "Sales Tax"}


def get_tax_rate(country_code: str) -> float:
    return _DEFAULT_TAX_RATES.get(country_code.upper(), 0.0)


def calculate_tax(amount: float, country_code: str) -> TaxCalculation:
    rate = get_tax_rate(country_code)
    tax_amount = round(amount * rate, 2)
    return TaxCalculation(
        country_code=country_code.upper(), tax_rate=rate, taxable_amount=amount,
        tax_amount=tax_amount, tax_name=_TAX_NAMES.get(country_code.upper(), "Tax"),
    )


def requires_tax_id_validation(country_code: str) -> bool:
    return country_code.upper() in {"IN", "GB", "DE", "FR", "AU", "SG", "AE"}


def validate_gstin(gstin: str) -> bool:
    import re
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.strip().upper()))


async def get_tax_report(db: Any, range_str: str = "30d", country_code: str | None = None) -> dict[str, Any]:
    return {"range": range_str, "country_code": country_code, "total_tax_collected_usd": 0.0, "by_country": {}}
