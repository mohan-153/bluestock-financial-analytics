from pathlib import Path

import pandas as pd

from src.etl.normalizer import normalize_year, normalize_ticker


# ============================================================
# DIRECTORIES
# ============================================================

RAW_DATA_DIR = Path("data/raw")
SUPPORTING_DATA_DIR = Path("data/supporting datasets")


# ============================================================
# DATASET DEFINITIONS
# ============================================================

CORE_FILES = {
    "companies": "companies.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "analysis": "analysis.xlsx",
    "documents": "documents.xlsx",
    "prosandcons": "prosandcons.xlsx",
}

SUPPORTING_FILES = {
    "sectors": "sectors.xlsx",
    "market_cap": "market_cap.xlsx",
    "stock_prices": "stock_prices.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "peer_groups": "peer_groups.xlsx",
}

FINANCIAL_DATASETS = {
    "profitandloss",
    "balancesheet",
    "cashflow",
}

# Only these datasets are annual financial datasets
# that need TTM removal and annual deduplication.
ANNUAL_DATASETS = {
    "profitandloss",
    "balancesheet",
    "cashflow",
}


# ============================================================
# BASIC EXCEL LOADERS
# ============================================================

def load_excel(filename: str) -> pd.DataFrame:
    """
    Load one of the 7 core Excel files.

    Core files use the second Excel row as the header.
    """

    file_path = RAW_DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    df = pd.read_excel(
        file_path,
        header=1,
    )

    return normalize_dataframe(df)


def load_supporting_excel(filename: str) -> pd.DataFrame:
    """
    Load one of the 5 supporting Excel files.

    Supporting files use the first Excel row as the header.
    """

    file_path = SUPPORTING_DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    df = pd.read_excel(
        file_path,
        header=0,
    )

    return normalize_dataframe(df)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply common normalization.

    Rules:
    - Strip column names.
    - Rename known source columns.
    - Normalize financial years.
    - Normalize company IDs.
    - Normalize tickers.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # --------------------------------------------------------
    # Standardize known source column names
    # --------------------------------------------------------

    df = df.rename(
        columns={
            "Year": "year",
            "Annual_Report": "annual_report",
        }
    )

    # --------------------------------------------------------
    # Normalize values
    # --------------------------------------------------------

    for column in df.columns:

        column_lower = (
            str(column)
            .strip()
            .lower()
        )

        # Financial year
        if column_lower in {
            "year",
            "financial_year",
            "fy",
        }:

            df[column] = df[column].apply(
                normalize_year
            )

        # Ticker
        elif column_lower in {
            "ticker",
            "symbol",
            "stock_ticker",
        }:

            df[column] = df[column].apply(
                normalize_ticker
            )

        # Company ID
        elif column_lower in {
            "company_id",
            "companyid",
        }:

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .str.upper()
            )

    return df


# ============================================================
# COMPANY ID NORMALIZATION
# ============================================================

def normalize_company_ids(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize company IDs.

    Known source typo:
        AGTL -> ATGL
    """

    df = df.copy()

    if "company_id" not in df.columns:
        return df

    df["company_id"] = (
        df["company_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["company_id"] = df["company_id"].replace(
        {
            "AGTL": "ATGL",
        }
    )

    return df


# ============================================================
# YEAR CLEANUP
# ============================================================

def remove_non_annual_rows(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove rows without a normalized financial year.

    TTM becomes None and is excluded from annual datasets.
    """

    df = df.copy()

    if "year" not in df.columns:
        return df

    return df[
        df["year"].notna()
    ].copy()


# ============================================================
# DQ-02 DUPLICATE HANDLING
# ============================================================

def deduplicate_annual_records(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove duplicate (company_id, year) records.

    Keep the last occurrence.
    """

    df = df.copy()

    required_columns = {
        "company_id",
        "year",
    }

    if not required_columns.issubset(
        df.columns
    ):
        return df

    df = df.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="last",
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# MASTER COMPANY LIST
# ============================================================

def get_master_company_ids(
    companies: pd.DataFrame,
) -> set[str]:
    """
    Return normalized company IDs from companies.xlsx.

    companies.xlsx stores the company identifier in `id`.
    """

    if "id" not in companies.columns:
        raise ValueError(
            "companies dataset must contain an 'id' column"
        )

    return set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )


# ============================================================
# CORE DATASET LOADING
# ============================================================

def load_dataset(
    name: str,
) -> pd.DataFrame:
    """
    Load one core dataset.
    """

    if name not in CORE_FILES:
        raise ValueError(
            f"Unknown dataset: {name}"
        )

    df = load_excel(
        CORE_FILES[name]
    )

    if name in FINANCIAL_DATASETS:

        df = normalize_company_ids(df)

        df = remove_non_annual_rows(df)

        df = deduplicate_annual_records(df)

    return df


def load_all_core_data() -> dict[str, pd.DataFrame]:
    """
    Load all seven core datasets.

    Financial datasets are restricted to
    the 92-company master list.
    """

    data = {}

    for name in CORE_FILES:
        data[name] = load_dataset(name)

    master_ids = get_master_company_ids(
        data["companies"]
    )

    for name in FINANCIAL_DATASETS:

        df = data[name].copy()

        if "company_id" not in df.columns:
            data[name] = df
            continue

        df = normalize_company_ids(df)

        df = df[
            df["company_id"].isin(
                master_ids
            )
        ].copy()

        df = remove_non_annual_rows(df)

        df = deduplicate_annual_records(df)

        data[name] = df

    return data


# ============================================================
# SUPPORTING DATASET LOADING
# ============================================================

def load_supporting_dataset(
    name: str,
) -> pd.DataFrame:
    """
    Load one supporting dataset.
    """

    if name not in SUPPORTING_FILES:
        raise ValueError(
            f"Unknown supporting dataset: {name}"
        )

    df = load_supporting_excel(
        SUPPORTING_FILES[name]
    )

    if "company_id" in df.columns:
        df = normalize_company_ids(df)

    if name in ANNUAL_DATASETS:

        df = remove_non_annual_rows(df)

        df = deduplicate_annual_records(df)

    return df


def load_all_supporting_data() -> dict[str, pd.DataFrame]:
    """
    Load all five supporting datasets.
    """

    data = {}

    for name in SUPPORTING_FILES:
        data[name] = load_supporting_dataset(
            name
        )

    return data


# ============================================================
# LOAD EVERYTHING
# ============================================================

def load_all_data() -> dict[str, pd.DataFrame]:
    """
    Load all 12 project datasets.
    """

    data = {}

    data.update(
        load_all_core_data()
    )

    data.update(
        load_all_supporting_data()
    )

    return data


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def load_companies() -> pd.DataFrame:
    """
    Load the companies master dataset.
    """

    return load_dataset(
        "companies"
    )