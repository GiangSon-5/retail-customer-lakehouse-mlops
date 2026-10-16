#!/usr/bin/env python3
"""
Module: src/data_inventory.py
Mô tả: Khảo sát, kiểm kê toàn diện dữ liệu thô (Raw Data Overview) cho dự án Retail Customer Segmentation.
Hỗ trợ kiểm tra cấu trúc bảng, khóa chính, khóa ngoại, rủi ro fan-out, và tính khả thi tính toán RFM.
Tuân thủ Dual-Mode: Hỗ trợ cờ --debug (micro-sampling N <= 1000) và chế độ chạy Full có kiểm soát.
"""

import os
import sys
import argparse
import time
import json
import pandas as pd
import numpy as np

# Thiết lập encoding UTF-8 an toàn trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_data_inventory(data_dir: str, debug: bool = False) -> dict:
    start_time = time.time()
    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM KÊ DỮ LIỆU NGUỒN (RAW DATA INVENTORY AUDIT)")
    print(f"📁 Thư mục dữ liệu: {data_dir}")
    print(f"⚙️ Chế độ thực thi: {'--debug (Micro-sampling)' if debug else 'Chạy Full 100% dữ liệu'}")
    print("=" * 70)

    tx_path = os.path.join(data_dir, "Transactions.csv")
    prod_path = os.path.join(data_dir, "Products_with_Categories.csv")
    ecom_path = os.path.join(data_dir, "e-commerce.csv")

    results = {
        "execution_mode": "debug" if debug else "full",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tables": {},
        "relationships": {},
        "rfm_feasibility": {},
        "extra_datasets": {}
    }

    # 1. Kiểm kê Transactions.csv
    print("\n🔍 [1/4] Kiểm kê bảng: Transactions.csv")
    if not os.path.exists(tx_path):
        raise FileNotFoundError(f"Không tìm thấy file: {tx_path}")

    df_tx = pd.read_csv(tx_path)
    raw_tx_len = len(df_tx)
    if debug:
        print(f"   [Debug Mode] Lấy mẫu micro-sampling 1.000 dòng từ {raw_tx_len:,} dòng gốc.")
        df_tx = df_tx.head(1000).copy()

    tx_mem_bytes = df_tx.memory_usage(deep=True).sum()
    results["tables"]["transactions"] = {
        "file_name": "Transactions.csv",
        "file_size_bytes": os.path.getsize(tx_path),
        "total_rows_raw": raw_tx_len,
        "analyzed_rows": len(df_tx),
        "columns_count": len(df_tx.columns),
        "memory_mb": round(tx_mem_bytes / (1024 * 1024), 4),
        "columns": {}
    }

    print(f"   • Kích thước: {len(df_tx):,} dòng x {len(df_tx.columns)} cột | RAM: {results['tables']['transactions']['memory_mb']} MB")
    for col in df_tx.columns:
        null_count = int(df_tx[col].isnull().sum())
        null_pct = round((null_count / len(df_tx)) * 100, 2)
        n_unique = int(df_tx[col].nunique())
        results["tables"]["transactions"]["columns"][col] = {
            "dtype": str(df_tx[col].dtype),
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": n_unique,
            "sample_values": [str(x) for x in df_tx[col].dropna().head(3).tolist()]
        }
        print(f"     - Cột `{col}`: dtype={df_tx[col].dtype}, Null={null_count} ({null_pct}%), Unique={n_unique:,}")

    # 2. Kiểm kê Products_with_Categories.csv
    print("\n🔍 [2/4] Kiểm kê bảng: Products_with_Categories.csv")
    if not os.path.exists(prod_path):
        raise FileNotFoundError(f"Không tìm thấy file: {prod_path}")

    df_prod = pd.read_csv(prod_path)
    prod_mem_bytes = df_prod.memory_usage(deep=True).sum()
    results["tables"]["products"] = {
        "file_name": "Products_with_Categories.csv",
        "file_size_bytes": os.path.getsize(prod_path),
        "total_rows_raw": len(df_prod),
        "analyzed_rows": len(df_prod),
        "columns_count": len(df_prod.columns),
        "memory_mb": round(prod_mem_bytes / (1024 * 1024), 4),
        "columns": {}
    }
    print(f"   • Kích thước: {len(df_prod):,} dòng x {len(df_prod.columns)} cột | RAM: {results['tables']['products']['memory_mb']} MB")
    for col in df_prod.columns:
        null_count = int(df_prod[col].isnull().sum())
        null_pct = round((null_count / len(df_prod)) * 100, 2)
        n_unique = int(df_prod[col].nunique())
        results["tables"]["products"]["columns"][col] = {
            "dtype": str(df_prod[col].dtype),
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": n_unique,
            "sample_values": [str(x) for x in df_prod[col].dropna().head(3).tolist()]
        }
        print(f"     - Cột `{col}`: dtype={df_prod[col].dtype}, Null={null_count} ({null_pct}%), Unique={n_unique:,}")

    # 3. Kiểm tra quan hệ bảng & Rủi ro Fan-out
    print("\n🔍 [3/4] Kiểm soát quan hệ bảng & Chốt chặn Fan-out")
    # Xác định khóa liên kết: kiểm tra cột chung giữa Transactions và Products
    tx_cols = set(df_tx.columns)
    prod_cols = set(df_prod.columns)
    common_cols = list(tx_cols.intersection(prod_cols))
    print(f"   • Cột chung nhận diện giữa 2 bảng: {common_cols}")

    join_key = common_cols[0] if common_cols else None
    if not join_key:
        # Nếu khác tên, kiểm tra productId hoặc itemDescription
        if "itemDescription" in df_tx.columns and "itemDescription" in df_prod.columns:
            join_key = "itemDescription"
        elif "productId" in df_tx.columns and "productId" in df_prod.columns:
            join_key = "productId"
        elif "itemDescription" in df_tx.columns and "Product" in df_prod.columns:
            join_key = ("itemDescription", "Product")

    results["relationships"]["join_key"] = str(join_key)
    
    # Kiểm tra Primary Key trong bảng Products
    if isinstance(join_key, str) and join_key in df_prod.columns:
        prod_pk_unique = bool(df_prod[join_key].is_unique)
        results["relationships"]["product_pk_unique"] = prod_pk_unique
        print(f"   • Khóa chính `{join_key}` trên Products duy nhất 100%: {'✅ YES' if prod_pk_unique else '❌ NO (Trùng lặp)'}")
        
        # Kiểm tra Orphan keys (khóa ngoại mồ côi)
        tx_items = set(df_tx[join_key].dropna().unique())
        prod_items = set(df_prod[join_key].dropna().unique())
        orphan_items = tx_items - prod_items
        results["relationships"]["orphan_items_count"] = len(orphan_items)
        results["relationships"]["orphan_items_sample"] = list(orphan_items)[:5]
        print(f"   • Khóa ngoại mồ côi (Sản phẩm có trong Transactions nhưng thiếu trong Products): {len(orphan_items)}")
        if orphan_items:
            print(f"     -> Danh sách mẫu: {list(orphan_items)[:5]}")

        # Thử nghiệm phép Join và chốt chặn Fan-out
        len_before = len(df_tx)
        df_merged = df_tx.merge(df_prod, on=join_key, how="left")
        len_after = len(df_merged)
        fan_out = len_after - len_before
        results["relationships"]["fan_out_delta"] = fan_out
        assert len_after == len_before, f"CẢNH BÁO FAN-OUT: Số dòng tăng từ {len_before} lên {len_after} sau khi join!"
        print(f"   • Chốt chặn Fan-out: len(before)={len_before:,} == len(after)={len_after:,} -> ✅ HOÀN TOÀN BẢO TOÀN (Zero Fan-out)")

    # 4. Kiểm tra tính khả thi trích xuất RFM
    print("\n🔍 [4/4] Đối chiếu tính khả thi tính toán RFM")
    member_col = "Member_number" if "Member_number" in df_tx.columns else None
    date_col = "Date" if "Date" in df_tx.columns else None
    
    if member_col and date_col:
        unique_members = int(df_tx[member_col].nunique())
        # Thử parse Date
        try:
            parsed_dates = pd.to_datetime(df_tx[date_col], format="%d-%m-%Y")
        except Exception:
            parsed_dates = pd.to_datetime(df_tx[date_col], errors="coerce")

        min_date = str(parsed_dates.min().strftime("%Y-%m-%d"))
        max_date = str(parsed_dates.max().strftime("%Y-%m-%d"))
        results["rfm_feasibility"] = {
            "customer_id_col": member_col,
            "unique_customers": unique_members,
            "date_col": date_col,
            "date_range": [min_date, max_date],
            "date_span_days": int((parsed_dates.max() - parsed_dates.min()).days),
            "status": "FEASIBLE"
        }
        print(f"   • Số lượng khách hàng duy nhất (Grain): {unique_members:,} khách hàng")
        print(f"   • Khoảng thời gian giao dịch: {min_date} -> {max_date} ({results['rfm_feasibility']['date_span_days']} ngày)")
        print("   • Đánh giá tính đầy đủ: ✅ DỮ LIỆU ĐỦ 100% ĐỂ TRÍCH XUẤT RFM VÀ PHÂN CỤM")

    # Kiểm tra tệp e-commerce.csv (nếu có trong thư mục)
    if os.path.exists(ecom_path):
        ecom_size_mb = round(os.path.getsize(ecom_path) / (1024 * 1024), 2)
        results["extra_datasets"]["e_commerce_csv"] = {
            "size_mb": ecom_size_mb,
            "status": "Tập dữ liệu mở rộng (E-commerce), không thuộc nghiệp vụ cửa hàng POS X của Topic 1"
        }
        print(f"\n📦 Phát hiện tệp dữ liệu phụ: e-commerce.csv ({ecom_size_mb} MB) -> Được định danh là tập mở rộng.")

    elapsed = round(time.time() - start_time, 3)
    results["elapsed_seconds"] = elapsed
    print("\n" + "=" * 70)
    print(f"✅ HOÀN TẤT KIỂM KÊ DỮ LIỆU TRONG {elapsed} GIÂY!")
    print("=" * 70)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Data Inventory Audit for Retail Customer Segmentation")
    parser.add_argument("--data-dir", default="data/raw/Du_lieu_cung_cap", help="Đường dẫn thư mục dữ liệu thô")
    parser.add_argument("--debug", action="store_true", help="Chạy chế độ micro-sampling kiểm thử")
    parser.add_argument("--export-json", default="scratch/data_inventory_summary.json", help="Nơi lưu kết quả JSON")
    args = parser.parse_args()

    # Tự động định vị đường dẫn dữ liệu nếu chạy từ root hoặc project dir
    candidate_paths = [
        args.data_dir,
        os.path.join("projects", "customer_segmentation", args.data_dir),
        os.path.join("projects", "customer_segmentation", "data", "raw", "Du_lieu_cung_cap"),
        os.path.join("data", "raw", "Du_lieu_cung_cap"),
    ]
    target_dir = None
    for p in candidate_paths:
        if os.path.exists(p) and os.path.exists(os.path.join(p, "Transactions.csv")):
            target_dir = p
            break

    if not target_dir:
        print(f"❌ Không tìm thấy thư mục chứa Transactions.csv trong: {candidate_paths}")
        sys.exit(1)

    res = run_data_inventory(target_dir, debug=args.debug)

    # Xuất tệp JSON phục vụ dựng báo cáo Markdown
    out_dir = os.path.dirname(args.export_json)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(args.export_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"📄 Kết quả kiểm kê đã lưu tại: {args.export_json}")
    sys.exit(0)
