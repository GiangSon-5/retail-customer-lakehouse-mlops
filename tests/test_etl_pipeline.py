"""Unit tests cho src/etl_pipeline.py.

Kiem thu cac chot chan:
1. Lam sach va dien gia thieu theo Median nganh hang (Category Median Imputation).
2. Tinh toan Recency, Frequency, Monetary chuan logic nghiep vu.
3. Chuan hoa StandardScaler khong bi ro ri.
4. Kiem toan doi soat du lieu Zero Data Loss.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pytest

from src.etl_pipeline import (
    clean_and_enrich_transactions,
    extract_rfm_features,
    scale_rfm_features,
    verify_integrity,
)


@pytest.fixture
def sample_raw_data():
    """Tao du lieu mau synthetic de kiem thu logic."""
    tx_data = {
        "Member_number": ["1001", "1001", "1002", "1003", "1003"],
        "Date": ["20-12-2015", "25-12-2015", "10-10-2015", "01-01-2015", "15-06-2015"],
        "productId": [1, 2, 1, 3, 4],
        "items": [2, 1, 3, 1, 2],
    }
    prod_data = {
        "productId": [1, 2, 3, 4],
        "productName": ["Milk", "Bread", "Apple", "Orange"],
        "Category": ["Dairy", "Bakery", "Fruit", "Fruit"],
        "price": [2.5, 1.0, 3.0, np.nan],  # San pham 4 thieu gia -> can dien median cua Fruit (3.0)
    }
    return pd.DataFrame(tx_data), pd.DataFrame(prod_data)


def test_clean_and_enrich_transactions(sample_raw_data):
    tx_df, prod_df = sample_raw_data
    silver_df = clean_and_enrich_transactions(tx_df, prod_df)

    # 1. Kiem tra so luong dong khong bi mat
    assert len(silver_df) == 5

    # 2. Kiem tra tinh dung dan cua Date ISO
    assert pd.api.types.is_datetime64_any_dtype(silver_df["transaction_date"])
    assert silver_df["year"].iloc[0] == 2015

    # 3. Kiem tra dien gia thieu (Imputation) cua Fruit (San pham 4)
    p4_row = silver_df[silver_df["productId"] == 4].iloc[0]
    assert p4_row["unit_price"] == 3.0  # Median cua Fruit (co Apple gia 3.0)
    assert p4_row["line_total_amount"] == 3.0 * 2  # unit_price * quantity = 6.0


def test_extract_rfm_features(sample_raw_data):
    tx_df, prod_df = sample_raw_data
    silver_df = clean_and_enrich_transactions(tx_df, prod_df)
    rfm_df = extract_rfm_features(silver_df)

    # 3 khach hang duy nhat: 1001, 1002, 1003
    assert len(rfm_df) == 3
    assert set(rfm_df["member_number"]) == {"1001", "1002", "1003"}

    # Khach 1001: ngay mua cuoi 25-12-2015 (cung la global_max_date) -> Recency = 0
    k1001 = rfm_df[rfm_df["member_number"] == "1001"].iloc[0]
    assert k1001["recency_days"] == 0
    assert k1001["frequency_count"] == 2  # 2 ngay khac nhau (20 va 25)
    # Monetary = (2 * 2.5) + (1 * 1.0) = 5.0 + 1.0 = 6.0
    assert k1001["monetary_total"] == 6.0


def test_scale_rfm_features(sample_raw_data):
    tx_df, prod_df = sample_raw_data
    silver_df = clean_and_enrich_transactions(tx_df, prod_df)
    rfm_df = extract_rfm_features(silver_df)
    scaled_df, scaler = scale_rfm_features(rfm_df)

    assert "r_scaled" in scaled_df.columns
    assert "f_scaled" in scaled_df.columns
    assert "m_scaled" in scaled_df.columns

    # Kiem tra Z-score co mean xap xi 0
    assert abs(scaled_df["r_scaled"].mean()) < 1e-6
    assert abs(scaled_df["m_scaled"].mean()) < 1e-6


def test_verify_integrity(sample_raw_data):
    tx_df, prod_df = sample_raw_data
    silver_df = clean_and_enrich_transactions(tx_df, prod_df)
    rfm_df = extract_rfm_features(silver_df)

    audit = verify_integrity(silver_df, rfm_df, is_debug=True)
    assert audit["customers_matched"] is True
    assert audit["total_rfm_customers"] == 3
    assert audit["negative_monetary"] == 0
