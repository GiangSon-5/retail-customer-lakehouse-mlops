"""Module ETL Pipeline & Trích xuất Đặc trưng RFM theo chuẩn AWS Lakehouse.

Triển khai Chặng 1 trong kiến trúc MLOps:
- Nạp và làm sạch dữ liệu giao dịch thô (Bronze Layer).
- Kết nối danh mục sản phẩm, chuẩn hóa ngày tháng ISO, xử lý missing price bằng median ngành hàng.
- Trích xuất 3 chỉ số Recency (R), Frequency (F), Monetary (M) cho từng khách hàng.
- Chuẩn hóa đặc trưng bằng StandardScaler phục vụ SageMaker K-Means (Gold Layer).
- Kiểm toán bảo toàn 100% khách hàng (3.898 / 3.898 khách hàng).
- Hỗ trợ chế độ --debug (micro-sampling N <= 1.000) phục vụ kiểm thử nhanh dưới 2 giây.
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

# Tự động nạp thư mục gốc của dự án vào sys.path để import chuẩn 'src.*'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 1. Khóa trần CPU <= 75% trước khi nạp thư viện toán học
from src.hardware import configure_cpu_governor
configure_cpu_governor(max_pct=0.75)


import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.utils import setup_logger, timer, get_project_root

logger = setup_logger("etl_pipeline")


def load_raw_data(data_dir: Path, is_debug: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Nạp dữ liệu nguồn thô từ thư mục Bronze (hoặc S3 local mount).
    
    Args:
        data_dir: Đường dẫn đến thư mục chứa file thô.
        is_debug: Nếu True, áp dụng micro-sampling (N <= 1.000).

    Returns:
        Tuple chứa (Transactions DataFrame, Products DataFrame).
    """
    tx_file = data_dir / "Transactions.csv"
    prod_file = data_dir / "Products_with_Categories.csv"

    if not tx_file.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp giao dịch: {tx_file}")
    if not prod_file.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp sản phẩm: {prod_file}")

    logger.info("Đang nạp dữ liệu thô từ: %s", data_dir)
    
    # Nạp danh mục sản phẩm (nhẹ ~5.8 KB)
    prod_df = pd.read_csv(prod_file)
    prod_df.columns = [c.strip() for c in prod_df.columns]

    # Nạp giao dịch
    if is_debug:
        logger.info("Chế độ DEBUG: Micro-sampling 1.000 dòng giao dịch đầu tiên.")
        tx_df = pd.read_csv(tx_file, nrows=1000)
    else:
        tx_df = pd.read_csv(tx_file)

    tx_df.columns = [c.strip() for c in tx_df.columns]
    logger.info("Đã nạp: %d dòng giao dịch, %d sản phẩm.", len(tx_df), len(prod_df))
    return tx_df, prod_df


def clean_and_enrich_transactions(
    tx_df: pd.DataFrame, 
    prod_df: pd.DataFrame
) -> pd.DataFrame:
    """Làm sạch, ép kiểu và làm giàu giao dịch (Tầng Silver).
    
    Quy tắc nghiệp vụ:
    - Lọc bỏ bản ghi thiếu Member_number.
    - Chuẩn hóa ngày giao dịch theo định dạng chuẩn ISO YYYY-MM-DD.
    - Left join với bảng sản phẩm theo productId.
    - Điền giá thiếu bằng Median Price theo Category (nếu không có thì lấy Median toàn hệ thống).
    - Tính tổng tiền dòng mặt hàng: line_total_amount = unit_price * quantity.
    """
    logger.info("Bắt đầu làm sạch và kết nối dữ liệu (Tầng Silver)...")
    df = tx_df.copy()

    # 1. Lọc bỏ Member_number rỗng/null
    df = df.dropna(subset=["Member_number"])
    df["member_number"] = df["Member_number"].astype(str).str.strip()

    # 2. Chuẩn hóa ngày giao dịch (Định dạng nguồn dd-MM-yyyy)
    df["transaction_date"] = pd.to_datetime(df["Date"].str.strip(), format="%d-%m-%Y")
    df["year"] = df["transaction_date"].dt.year
    df["month"] = df["transaction_date"].dt.month

    # 3. Chuẩn hóa productId để join
    df["productId"] = pd.to_numeric(df["productId"], errors="coerce").fillna(-1).astype(int)
    prod = prod_df.copy()
    prod["productId"] = pd.to_numeric(prod["productId"], errors="coerce").fillna(-1).astype(int)

    # Đổi tên cột giá sản phẩm sang chuẩn thống nhất
    if "price" in prod.columns:
        prod = prod.rename(columns={"price": "unit_price"})
    elif "Price" in prod.columns:
        prod = prod.rename(columns={"Price": "unit_price"})

    if "Category" in prod.columns:
        prod = prod.rename(columns={"Category": "category"})

    # 4. Tính toán Median Price theo ngành hàng (Category Median Imputation)
    category_medians = prod.groupby("category")["unit_price"].median().to_dict()
    global_median_price = prod["unit_price"].median()
    if pd.isna(global_median_price) or global_median_price <= 0:
        global_median_price = 15000.0  # Mức sàn tối thiểu theo tài liệu STTM

    # 5. Left Join giao dịch với sản phẩm
    merged = pd.merge(df, prod, on="productId", how="left")

    # 6. Điền giá thiếu theo đúng logic nghiệp vụ STTM
    def fill_price(row: pd.Series) -> float:
        if pd.notna(row["unit_price"]) and row["unit_price"] > 0:
            return float(row["unit_price"])
        cat = row.get("category")
        if pd.notna(cat) and cat in category_medians and pd.notna(category_medians[cat]):
            return float(category_medians[cat])
        return float(global_median_price)

    merged["unit_price"] = merged.apply(fill_price, axis=1)
    merged["category"] = merged["category"].fillna("General Grocery")

    # 7. Số lượng mặt hàng (Quantity) và Tổng tiền dòng hàng
    quantity_col = "items" if "items" in merged.columns else ("Items" if "Items" in merged.columns else None)
    if quantity_col:
        merged["quantity"] = pd.to_numeric(merged[quantity_col], errors="coerce").fillna(1).astype(int)
        merged["quantity"] = merged["quantity"].apply(lambda q: max(1, q))
    else:
        merged["quantity"] = 1

    merged["line_total_amount"] = merged["unit_price"] * merged["quantity"]

    # Chọn lọc cột cho Tầng Silver
    silver_cols = [
        "member_number",
        "transaction_date",
        "year",
        "month",
        "productId",
        "category",
        "unit_price",
        "quantity",
        "line_total_amount",
    ]
    if "productName" in merged.columns:
        merged["product_name"] = merged["productName"].fillna(merged.get("Items", "Unknown"))
        silver_cols.append("product_name")

    silver_df = merged[silver_cols].copy()
    logger.info("Hoàn thành Tầng Silver: %d bản ghi đã làm sạch.", len(silver_df))
    return silver_df


def extract_rfm_features(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Trích xuất 3 chỉ số Recency, Frequency, Monetary cấp khách hàng (Tầng Gold).
    
    Công thức:
    - Recency (R): Số ngày từ lần giao dịch gần nhất của khách đến ngày mới nhất toàn dataset.
    - Frequency (F): Tổng số ngày phát sinh giao dịch duy nhất của khách hàng.
    - Monetary (M): Tổng chi tiêu tích lũy của khách hàng.
    """
    logger.info("Bắt đầu trích xuất đặc trưng RFM cấp khách hàng...")
    global_max_date = clean_df["transaction_date"].max()
    logger.info("Mốc thời gian tính Recency (Global Max Date): %s", global_max_date.strftime("%Y-%m-%d"))

    # Gom nhóm theo member_number bằng Vectorized Aggregations
    rfm = clean_df.groupby("member_number").agg(
        last_date=("transaction_date", "max"),
        frequency_count=("transaction_date", "nunique"),
        monetary_total=("line_total_amount", "sum")
    ).reset_index()

    # Tính Recency (Số ngày)
    rfm["recency_days"] = (global_max_date - rfm["last_date"]).dt.days
    rfm = rfm.drop(columns=["last_date"])

    # Ép kiểu dữ liệu chuẩn
    rfm["recency_days"] = rfm["recency_days"].astype(int)
    rfm["frequency_count"] = rfm["frequency_count"].astype(int)
    rfm["monetary_total"] = rfm["monetary_total"].round(2)

    logger.info("Đã trích xuất RFM cho %d khách hàng duy nhất.", len(rfm))
    return rfm


def scale_rfm_features(rfm_df: pd.DataFrame) -> Tuple[pd.DataFrame, StandardScaler]:
    """Chuẩn hóa thang đo đặc trưng RFM bằng StandardScaler cho thuật toán K-Means.
    
    Tạo ra các cột chuẩn hóa: r_scaled, f_scaled, m_scaled.
    """
    logger.info("Tiến hành chuẩn hóa thang đo StandardScaler (Z-score)...")
    scaled_df = rfm_df.copy()
    features = ["recency_days", "frequency_count", "monetary_total"]
    
    scaler = StandardScaler()
    scaled_vals = scaler.fit_transform(scaled_df[features])

    scaled_df["r_scaled"] = scaled_vals[:, 0]
    scaled_df["f_scaled"] = scaled_vals[:, 1]
    scaled_df["m_scaled"] = scaled_vals[:, 2]

    return scaled_df, scaler


def verify_integrity(
    clean_df: pd.DataFrame, 
    rfm_df: pd.DataFrame, 
    is_debug: bool = False
) -> Dict[str, Any]:
    """Kiểm toán đối soát dữ liệu đảm bảo Zero Data Loss theo chuẩn UAT.
    
    Kiểm tra:
    1. Số khách hàng duy nhất trong clean_df == số dòng trong rfm_df.
    2. Nếu không ở chế độ debug: Số khách hàng bắt buộc khớp chính xác 3.898.
    3. Không có giá trị âm hoặc null trong Recency, Frequency, Monetary.
    """
    logger.info("Thực hiện kiểm toán đối soát chất lượng dữ liệu (Data Quality Audit)...")
    unique_tx_customers = clean_df["member_number"].nunique()
    total_rfm_customers = len(rfm_df)

    results = {
        "unique_raw_customers": unique_tx_customers,
        "total_rfm_customers": total_rfm_customers,
        "customers_matched": unique_tx_customers == total_rfm_customers,
        "null_counts": rfm_df[["recency_days", "frequency_count", "monetary_total"]].isna().sum().to_dict(),
        "negative_monetary": int((rfm_df["monetary_total"] <= 0).sum()),
    }

    assert results["customers_matched"], (
        f"Lỗi thất thoát khách hàng: Raw có {unique_tx_customers} nhưng RFM có {total_rfm_customers}!"
    )
    assert sum(results["null_counts"].values()) == 0, f"Phát hiện giá trị null trong RFM: {results['null_counts']}"
    assert results["negative_monetary"] == 0, f"Phát hiện tổng tiền chi tiêu <= 0: {results['negative_monetary']} khách"

    if not is_debug:
        expected_customers = 3898
        assert total_rfm_customers == expected_customers, (
            f"Lỗi đối soát UAT: Kỳ vọng đúng {expected_customers} khách hàng nhưng thực tế có {total_rfm_customers}!"
        )
        logger.info("XÁC NHẬN ĐỐI SOÁT UAT: Khớp chính xác 100% (3.898/3.898 khách hàng)!")
    else:
        logger.info("XÁC NHẬN ĐỐI SOÁT DEBUG: Hợp lệ với %d khách hàng mẫu.", total_rfm_customers)

    return results


def save_medallion_outputs(
    silver_df: pd.DataFrame, 
    gold_df: pd.DataFrame, 
    output_dir: Path, 
    is_debug: bool = False
) -> None:
    """Lưu trữ dữ liệu vào thư mục Medallion định dạng Apache Parquet."""
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = "debug_" if is_debug else ""

    silver_path = output_dir / f"{prefix}silver_transactions.parquet"
    gold_path = output_dir / f"{prefix}customer_rfm_features.parquet"

    logger.info("Đang ghi Tầng Silver: %s", silver_path)
    silver_df.to_parquet(silver_path, index=False, compression="snappy")

    logger.info("Đang ghi Tầng Gold: %s", gold_path)
    gold_df.to_parquet(gold_path, index=False, compression="snappy")
    logger.info("Ghi nhận thành công các tầng dữ liệu Lakehouse!")


def run_pipeline(
    data_dir: Path, 
    output_dir: Path, 
    is_debug: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Hàm điều phối toàn bộ chu trình ETL."""
    with timer(f"ETL Pipeline ({'DEBUG' if is_debug else 'FULL'})", logger=logger):
        # 1. Nạp dữ liệu
        tx_df, prod_df = load_raw_data(data_dir=data_dir, is_debug=is_debug)

        # 2. Làm sạch & làm giàu (Silver)
        silver_df = clean_and_enrich_transactions(tx_df=tx_df, prod_df=prod_df)

        # 3. Trích xuất RFM (Gold)
        rfm_df = extract_rfm_features(clean_df=silver_df)

        # 4. Chuẩn hóa đặc trưng
        gold_df, scaler = scale_rfm_features(rfm_df=rfm_df)

        # 5. Kiểm toán đối soát dữ liệu
        verify_integrity(clean_df=silver_df, rfm_df=gold_df, is_debug=is_debug)

        # 6. Lưu trữ đầu ra Medallion
        save_medallion_outputs(silver_df=silver_df, gold_df=gold_df, output_dir=output_dir, is_debug=is_debug)

        return silver_df, gold_df


def parse_args() -> argparse.Namespace:
    """Phân tích các đối số dòng lệnh CLI."""
    parser = argparse.ArgumentParser(description="Retail Customer Segmentation ETL Pipeline")
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Bật chế độ kiểm thử micro-sampling (1.000 dòng, runtime < 2s)"
    )
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default=None, 
        help="Đường dẫn thư mục dữ liệu thô (mặc định: data/raw/Du_lieu_cung_cap)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default=None, 
        help="Đường dẫn thư mục đầu ra (mặc định: data/processed)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    project_root = get_project_root()

    raw_dir = Path(args.data_dir) if args.data_dir else project_root / "data" / "raw" / "Du_lieu_cung_cap"
    proc_dir = Path(args.output_dir) if args.output_dir else project_root / "data" / "processed"

    run_pipeline(data_dir=raw_dir, output_dir=proc_dir, is_debug=args.debug)
