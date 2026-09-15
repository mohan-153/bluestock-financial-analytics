import re
from typing import Any
import pandas as pd

def normalize_year(value: Any):
    """
    Normalize financial-year values into YYYY-MM format.

    Examples:
        2024       -> "2024-03"
        "2024"     -> "2024-03"
        "FY2024"   -> "2024-03"
        "2024-25"  -> "2024-03"
        "Mar 2024" -> "2024-03"
        "Mar-24"   -> "2024-03"
        "Mar 24"   -> "2024-03"
        "Dec 2012" -> "2012-12"
        "TTM"      -> None
        None       -> None
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # TTM is not a financial year.
    if text.upper() == "TTM":
        return None

    # Already normalized: YYYY-MM
    match = re.fullmatch(r"(\d{4})-(\d{2})", text)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    # Month + full year:
    # Mar 2024
    # Mar-2024
    # Mar/2024
    match = re.fullmatch(
        r"([A-Za-z]{3,9})[\s/-]+(\d{4})",
        text,
    )

    if match:
        month_text = match.group(1).lower()
        year = int(match.group(2))

        months = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }

        month = months.get(month_text)

        if month:
            return f"{year:04d}-{month:02d}"

    # Month + two-digit year:
    # Mar-24
    # Mar 24
    match = re.fullmatch(
        r"([A-Za-z]{3,9})[\s/-]+(\d{2})",
        text,
    )

    if match:
        month_text = match.group(1).lower()
        short_year = int(match.group(2))

        months = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }

        month = months.get(month_text)

        if month:
            # Financial datasets use 20xx for these years.
            year = 2000 + short_year
            return f"{year:04d}-{month:02d}"

    # FY2024
    match = re.fullmatch(
        r"FY[\s-]?(\d{4})",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return f"{int(match.group(1)):04d}-03"

    # 2024-25
    match = re.fullmatch(
        r"(\d{4})-(\d{2})",
        text,
    )

    if match:
        return f"{int(match.group(1)):04d}-03"

    # Plain four-digit year
    match = re.fullmatch(r"(\d{4})", text)

    if match:
        return f"{int(match.group(1)):04d}-03"

    return None


def normalize_ticker(value):
    """
    Standardize a stock ticker.
    """
    if pd.isna(value):
        return None

    ticker = str(value).strip().upper()

    if not ticker:
        return None

    return ticker