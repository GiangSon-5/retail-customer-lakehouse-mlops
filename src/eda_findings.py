#!/usr/bin/env python3
"""
================================================================================
Module: src/eda_findings.py
Dự án: Retail Customer Segmentation & AWS Medallion Lakehouse
Trạm thực thi: Trạm 3 - EDA Before Cleaning (Khám Phá Dữ Liệu Thô 3 Tầng Thích Ứng)
================================================================================
Mục tiêu:
    - Khám phá 100% các cột dữ liệu thô (Transactions.csv & Products_with_Categories.csv).
    - Quét rà soát missing ngầm, sentinel values (MCAR/MAR/MNAR).
    - Phân tích 3 tầng: Đơn biến (Univariate - 4 mô-men), Hai biến (Bivariate - Num/Cat, Cat/Cat),
      Đa biến & Chuỗi thời gian (Multivariate & Time Series Dynamics).
    - Tạo 5 biểu đồ trực quan hóa dữ liệu độc bản chuẩn 300 DPI tại reports/imgs/.
    - Xuất số liệu thống kê đầy đủ ra dictionary/JSON để phục vụ báo cáo.
    - Hỗ trợ chế độ --debug (micro-sampling N <= 1000) và chế độ chạy Full có kiểm soát.
================================================================================
"""

import os
import sys
import argparse
import time
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')  # Headless backend an toàn trên mọi hệ điều hành
import matplotlib.pyplot as plt
import seaborn as sns

# Đảm bảo in UTF-8 an toàn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def configure_plot_style():
    """Thiết lập phong cách biểu đồ khoa học chuẩn Grandmaster Data Storytelling."""
    sns.set_theme(style="whitegrid", font="sans-serif")
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
    plt.rcParams["axes.edgecolor"] = "#cbd5e1"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["grid.color"] = "#f1f5f9"
    plt.rcParams["grid.linestyle"] = "--"


def scan_sentinel_values(df: pd.DataFrame) -> dict:
    """Quét các giá trị sentinel / missing ngầm phổ biến."""
    sentinels = [-1, -999, 999, 0, "null", "none", "nan", "unknown", "n/a", " ", "", "1900-01-01"]
    report = {}
    for col in df.columns:
        col_report = {}
        # Explicit NaN
        null_count = int(df[col].isna().sum())
        null_pct = round(null_count / len(df) * 100, 2)
        col_report["explicit_null"] = {"count": null_count, "pct": null_pct}

        # Check sentinel occurrences
        sentinel_counts = {}
        for s in sentinels:
            if df[col].dtype == "object":
                count = int((df[col].astype(str).str.strip().str.lower() == str(s).lower()).sum())
            else:
                count = int((df[col] == s).sum()) if isinstance(s, (int, float)) else 0
            if count > 0:
                sentinel_counts[str(s)] = count

        col_report["sentinels_detected"] = sentinel_counts
        report[col] = col_report
    return report


def run_eda_pipeline(data_dir: str = None, s3_bucket: str = None, output_img_dir: str = None, debug: bool = False) -> dict:
    start_time = time.time()
    print("=" * 70)
    print("🔍 BẮT ĐẦU DÂY CHUYỀN TRẠM 3: EDA BEFORE CLEANING")
    if s3_bucket:
        print(f"☁️ Nguồn dữ liệu S3 Lakehouse: s3://{s3_bucket}/raw/")
        tx_path = f"s3://{s3_bucket}/raw/Transactions.csv"
        prod_path = f"s3://{s3_bucket}/raw/Products_with_Categories.csv"
    else:
        print(f"📁 Thư mục dữ liệu cục bộ: {data_dir}")
        tx_path = os.path.join(data_dir, "Transactions.csv")
        prod_path = os.path.join(data_dir, "Products_with_Categories.csv")
        if not os.path.exists(tx_path) or not os.path.exists(prod_path):
            raise FileNotFoundError(f"Không tìm thấy file Transactions.csv hoặc Products_with_Categories.csv tại {data_dir}")

    print(f"🖼️ Thư mục ảnh xuất: {output_img_dir}")
    print(f"⚙️ Chế độ thực thi: {'--debug (Micro-sampling N=100)' if debug else 'Chạy Full 100% dữ liệu'}")
    print("=" * 70)

    os.makedirs(output_img_dir, exist_ok=True)
    configure_plot_style()

    # 1. Nạp dữ liệu thô
    df_tx = pd.read_csv(tx_path)
    df_prod = pd.read_csv(prod_path)

    raw_tx_len = len(df_tx)
    if debug:
        print(f"   [Debug Mode] Lấy mẫu micro-sampling 100 dòng từ {raw_tx_len:,} dòng gốc.")
        df_tx = df_tx.head(100).copy()

    # Chuẩn hóa cột Ngày tháng phục vụ phân tích
    df_tx["Date_dt"] = pd.to_datetime(df_tx["Date"], format="%d-%m-%Y")

    # Kết nối bảng để có đầy đủ thông tin giao dịch và danh mục hàng hóa
    df_merged = df_tx.merge(df_prod, on="productId", how="inner")
    df_merged["Line_Total"] = df_merged["items"] * df_merged["price"]

    # 2. Khảo sát Sentinel & Missing ngầm
    print("\n🔍 [1/5] Quét giá trị Sentinel và Missing ngầm...")
    sentinel_report = scan_sentinel_values(df_merged)

    # 3. Phân tích Đơn biến (Univariate Analysis)
    print("\n📊 [2/5] Phân tích Đơn biến (4 Mô-men thống kê & Hình dạng phân phối)...")
    numeric_cols = ["items", "price", "Line_Total"]
    num_stats = {}
    for col in numeric_cols:
        series = df_merged[col]
        q1 = float(np.percentile(series, 25))
        median = float(np.percentile(series, 50))
        q3 = float(np.percentile(series, 75))
        iqr = q3 - q1
        mean = float(series.mean())
        std = float(series.std())
        skew = float(stats.skew(series))
        kurt = float(stats.kurtosis(series))
        
        # Outlier counts (Tukey 1.5 IQR & 3.0 IQR)
        upper_15 = q3 + 1.5 * iqr
        upper_30 = q3 + 3.0 * iqr
        outliers_15 = int((series > upper_15).sum())
        outliers_30 = int((series > upper_30).sum())

        # Zero inflation check
        zero_count = int((series == 0).sum())
        zero_pct = round(zero_count / len(series) * 100, 2)

        num_stats[col] = {
            "count": int(len(series)),
            "min": float(series.min()),
            "q1": q1,
            "median": median,
            "mean": round(mean, 2),
            "q3": q3,
            "max": float(series.max()),
            "std": round(std, 2),
            "iqr": round(iqr, 2),
            "skewness": round(skew, 2),
            "kurtosis": round(kurt, 2),
            "outliers_tukey_1.5": {"count": outliers_15, "pct": round(outliers_15 / len(series) * 100, 2)},
            "outliers_extreme_3.0": {"count": outliers_30, "pct": round(outliers_30 / len(series) * 100, 2)},
            "zero_inflation": {"count": zero_count, "pct": zero_pct}
        }

    # Tổng hợp phân vị RFM ở cấp độ Khách Hàng (Customer Grain)
    t_ref = pd.Timestamp("2015-12-31")
    rfm_df = df_merged.groupby("Member_number").agg(
        Recency=("Date_dt", lambda x: (t_ref - x.max()).days),
        Frequency=("Date_dt", "nunique"),
        Monetary=("Line_Total", "sum"),
        Total_Items=("items", "sum")
    ).reset_index()

    rfm_stats = {}
    for col in ["Recency", "Frequency", "Monetary", "Total_Items"]:
        series = rfm_df[col]
        rfm_stats[col] = {
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "std": round(float(series.std()), 2),
            "min": float(series.min()),
            "max": float(series.max()),
            "skewness": round(float(stats.skew(series)), 2),
            "kurtosis": round(float(stats.kurtosis(series)), 2)
        }

    # Phân tích Biến Phân Loại (Categorical Profiling - Category)
    cat_summary = df_merged["Category"].value_counts().reset_index()
    cat_summary.columns = ["Category", "Transaction_Count"]
    cat_summary["Pct"] = round(cat_summary["Transaction_Count"] / len(df_merged) * 100, 2)
    cat_revenue = df_merged.groupby("Category")["Line_Total"].sum().reset_index()
    cat_summary = cat_summary.merge(cat_revenue, on="Category")
    cat_summary = cat_summary.sort_values(by="Line_Total", ascending=False).reset_index(drop=True)
    cat_summary["Rev_Pct"] = round(cat_summary["Line_Total"] / cat_summary["Line_Total"].sum() * 100, 2)
    cat_summary["Cumulative_Rev_Pct"] = round(cat_summary["Rev_Pct"].cumsum(), 2)

    cat_breakdown = cat_summary.to_dict(orient="records")

    # 4. Phân tích Hai biến & Thống kê suy luận (Bivariate Analysis)
    print("\n📈 [3/5] Phân tích Hai biến (ANOVA, Kruskal-Wallis, Correlation Ratio)...")
    # Kiểm định phương sai Line_Total theo Category (Num vs Cat)
    groups = [group["Line_Total"].values for _, group in df_merged.groupby("Category")]
    kw_stat, kw_p = stats.kruskal(*groups)
    f_stat, f_p = stats.f_oneway(*groups)

    # Tính Eta-squared (Correlation Ratio) cho Category vs Line_Total
    grand_mean = df_merged["Line_Total"].mean()
    ss_total = ((df_merged["Line_Total"] - grand_mean) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    eta_squared = round(float(ss_between / ss_total), 4) if ss_total > 0 else 0.0

    bivariate_results = {
        "num_vs_cat": {
            "feature": "Category",
            "target_metric": "Line_Total",
            "kruskal_h": round(float(kw_stat), 2),
            "kruskal_p": float(kw_p),
            "anova_f": round(float(f_stat), 2),
            "anova_p": float(f_p),
            "eta_squared": eta_squared,
            "interpretation": f"Category chi phối {eta_squared*100:.2f}% phương sai giá trị đơn hàng (Line_Total)."
        }
    }

    # 5. Phân tích Đa biến & Chuỗi thời gian (Multivariate & Time Series)
    print("\n📉 [4/5] Phân tích Đa biến & Động lực Chuỗi thời gian...")
    # Tương quan Spearman RFM
    spearman_rfm = rfm_df[["Recency", "Frequency", "Monetary", "Total_Items"]].corr(method="spearman").round(3).to_dict()

    # Thống kê Chuỗi thời gian theo Ngày & Thứ trong tuần
    df_merged["DayOfWeek"] = df_merged["Date_dt"].dt.day_name()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_counts = df_merged["DayOfWeek"].value_counts().reindex(dow_order).to_dict()

    df_daily = df_merged.groupby(df_merged["Date_dt"].dt.date).agg(
        Transactions=("productId", "count"),
        Revenue=("Line_Total", "sum")
    ).reset_index()

    # 6. Trực quan hóa dữ liệu (Purpose-Driven Plots)
    print("\n🎨 [5/5] Sinh 5 biểu đồ khoa học chuẩn Grandmaster 300 DPI...")

    # Biểu đồ 1: RFM Univariate Distributions
    fig1, axes1 = plt.subplots(1, 3, figsize=(16, 5))
    metrics_info = [
        ("Recency", "Khoảng cách mua gần nhất (Ngày)", "#0284c7"),
        ("Frequency", "Tần suất mua sắm (Số phiên)", "#0f766e"),
        ("Monetary", "Tổng giá trị chi tiêu (USD)", "#e11d48")
    ]
    for ax, (m_col, m_label, m_color) in zip(axes1, metrics_info):
        data = rfm_df[m_col]
        sns.histplot(data, kde=True, ax=ax, color=m_color, bins=25, alpha=0.6, edgecolor=None)
        ax.set_title(f"Phân phối {m_col}\nSkew: {rfm_stats[m_col]['skewness']} | Kurt: {rfm_stats[m_col]['kurtosis']}", fontsize=11, fontweight="bold")
        ax.set_xlabel(m_label, fontsize=10)
        ax.set_ylabel("Mật độ / Số khách hàng", fontsize=10)
        ax.axvline(data.median(), color="#1e293b", linestyle="--", linewidth=1.2, label=f"Median: {data.median():.1f}")
        ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", loc="upper right")
    plt.tight_layout()
    img1_path = os.path.join(output_img_dir, "01_rfm_univariate_distribution.png")
    fig1.savefig(img1_path, dpi=300, bbox_inches="tight")
    plt.close(fig1)
    print(f"   ✓ [Rendered] {img1_path}")

    # Biểu đồ 2: Category Revenue & Pareto 80/20
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    cat_df_plot = cat_summary.sort_values(by="Line_Total", ascending=False)
    ax2_twin = ax2.twinx()
    bars = ax2.bar(cat_df_plot["Category"], cat_df_plot["Line_Total"], color="#0284c7", alpha=0.75, width=0.6, label="Doanh thu (USD)")
    ax2_twin.plot(cat_df_plot["Category"], cat_df_plot["Cumulative_Rev_Pct"], color="#e11d48", marker="o", linewidth=2.0, label="Tỷ lệ tích lũy Pareto (%)")
    ax2_twin.axhline(80, color="#d97706", linestyle="--", linewidth=1.2, label="Ngưỡng Pareto 80%")
    ax2.set_xticks(range(len(cat_df_plot)))
    ax2.set_xticklabels(cat_df_plot["Category"], rotation=35, ha="right", fontsize=9)
    ax2.set_ylabel("Tổng Doanh Thu (USD)", fontsize=11, fontweight="bold", color="#0284c7")
    ax2_twin.set_ylabel("Tỷ lệ tích lũy (%)", fontsize=11, fontweight="bold", color="#e11d48")
    ax2_twin.set_ylim(0, 105)
    ax2.set_title("Phân Tích Cơ Cấu Ngành Hàng & Quy Luật Pareto 80/20 (11 Danh Mục)", fontsize=13, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2_twin.grid(False)
    plt.tight_layout()
    img2_path = os.path.join(output_img_dir, "02_category_revenue_pareto.png")
    fig2.savefig(img2_path, dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print(f"   ✓ [Rendered] {img2_path}")

    # Biểu đồ 3: Bivariate Boxplot Category vs Line_Total
    fig3, ax3 = plt.subplots(figsize=(13, 6))
    sns.boxplot(
        data=df_merged,
        x="Category",
        y="Line_Total",
        hue="Category",
        legend=False,
        order=cat_df_plot["Category"],
        palette="viridis",
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "red", "markeredgecolor": "red", "markersize": 5},
        ax=ax3
    )
    ax3.set_yscale("log")
    ax3.set_xticks(range(len(cat_df_plot)))
    ax3.set_xticklabels(cat_df_plot["Category"], rotation=35, ha="right", fontsize=9)
    ax3.set_title(f"Phân Phối Giá Trị Đơn Hàng (Line_Total - Log Scale) Theo 11 Ngành Hàng\nKruskal-Wallis H={kw_stat:.1f} (p < 0.001) | ANOVA F={f_stat:.1f} | η²={eta_squared:.4f}", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Giá trị đơn hàng (USD - Thang Log)", fontsize=10)
    ax3.set_xlabel("Ngành hàng (Category)", fontsize=10)
    plt.tight_layout()
    img3_path = os.path.join(output_img_dir, "03_bivariate_category_basket_boxplots.png")
    fig3.savefig(img3_path, dpi=300, bbox_inches="tight")
    plt.close(fig3)
    print(f"   ✓ [Rendered] {img3_path}")

    # Biểu đồ 4: Time Series Dynamics & Day of Week Seasonality
    fig4, (ax4_top, ax4_bottom) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [2.5, 1]})
    df_daily["Date_dt"] = pd.to_datetime(df_daily["Date_dt"])
    df_daily["Rolling_7d"] = df_daily["Transactions"].rolling(7, center=True).mean()
    ax4_top.plot(df_daily["Date_dt"], df_daily["Transactions"], color="#94a3b8", alpha=0.5, linewidth=0.8, label="Giao dịch hàng ngày")
    ax4_top.plot(df_daily["Date_dt"], df_daily["Rolling_7d"], color="#0284c7", linewidth=2.0, label="Trung bình trượt 7 ngày (7-day MA)")
    ax4_top.set_title("Động Lực Chuỗi Thời Gian: Tần Suất Giao Dịch Hàng Ngày (2014 - 2015)", fontsize=12, fontweight="bold")
    ax4_top.set_ylabel("Số giao dịch POS", fontsize=10)
    ax4_top.legend(frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1", loc="upper right")
    ax4_top.grid(True, linestyle="--", alpha=0.5)

    dow_series = pd.Series(dow_counts)
    dow_colors = ["#0284c7" if d not in ["Saturday", "Sunday"] else "#e11d48" for d in dow_series.index]
    ax4_bottom.bar(dow_series.index, dow_series.values, color=dow_colors, alpha=0.8, width=0.5)
    ax4_bottom.set_title("Hiệu Ứng Chu Kỳ Tuần (Day-of-Week Seasonality): Phân Bổ Giao Dịch Từ Thứ 2 Đến Chủ Nhật", fontsize=11, fontweight="bold")
    ax4_bottom.set_ylabel("Tổng giao dịch", fontsize=10)
    for idx, val in enumerate(dow_series.values):
        ax4_bottom.text(idx, val * 0.85, f"{val:,}", ha="center", color="#ffffff", fontweight="bold", fontsize=9)
    plt.tight_layout()
    img4_path = os.path.join(output_img_dir, "04_timeseries_weekly_seasonality.png")
    fig4.savefig(img4_path, dpi=300, bbox_inches="tight")
    plt.close(fig4)
    print(f"   ✓ [Rendered] {img4_path}")

    # Biểu đồ 5: Multivariate Spearman Correlation Matrix
    fig5, ax5 = plt.subplots(figsize=(8, 6))
    corr_matrix = rfm_df[["Recency", "Frequency", "Monetary", "Total_Items"]].corr(method="spearman")
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="Blues", cbar=True, ax=ax5, vmin=-1, vmax=1, square=True)
    ax5.set_title("Ma Trận Tương Quan Thứ Hạng Spearman (Customer RFM Space)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    img5_path = os.path.join(output_img_dir, "05_multivariate_spearman_correlation.png")
    fig5.savefig(img5_path, dpi=300, bbox_inches="tight")
    plt.close(fig5)
    print(f"   ✓ [Rendered] {img5_path}")

    elapsed = round(time.time() - start_time, 2)
    print(f"\n✅ HOÀN TẤT EDA PIPELINE TRONG {elapsed} GIÂY!")

    output_results = {
        "execution_mode": "debug" if debug else "full",
        "elapsed_seconds": elapsed,
        "sample_size": len(df_tx),
        "sentinel_audit": sentinel_report,
        "numeric_moments": num_stats,
        "rfm_customer_moments": rfm_stats,
        "category_breakdown": cat_breakdown,
        "bivariate": bivariate_results,
        "spearman_rfm": spearman_rfm,
        "dow_counts": dow_counts,
        "rendered_images": [
            "01_rfm_univariate_distribution.png",
            "02_category_revenue_pareto.png",
            "03_bivariate_category_basket_boxplots.png",
            "04_timeseries_weekly_seasonality.png",
            "05_multivariate_spearman_correlation.png"
        ]
    }
    return output_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EDA Before Cleaning Pipeline")
    parser.add_argument("--debug", action="store_true", help="Chạy chế độ micro-sampling kiểm thử nhanh")
    parser.add_argument("--s3-bucket", default=None, help="Tên S3 Bucket chứa dữ liệu Bronze (ví dụ: retail-customer-lakehouse-876760932342-bronze)")
    parser.add_argument("--data-dir", default=None, help="Đường dẫn thư mục chứa dữ liệu thô cục bộ")
    parser.add_argument("--output-img-dir", default=None, help="Đường dẫn xuất ảnh biểu đồ")
    args = parser.parse_args()

    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    img_directory = args.output_img_dir or os.path.join(project_dir, "reports", "imgs")

    if args.s3_bucket:
        res = run_eda_pipeline(s3_bucket=args.s3_bucket, output_img_dir=img_directory, debug=args.debug)
    else:
        candidate_paths = [
            args.data_dir,
            os.path.join(project_dir, "data", "raw", "Du_lieu_cung_cap"),
            os.path.join(project_dir, "data"),
            os.path.join("data", "raw", "Du_lieu_cung_cap"),
            os.path.join("projects", "customer_segmentation", "data", "raw", "Du_lieu_cung_cap"),
        ]
        data_directory = None
        for p in candidate_paths:
            if p and os.path.exists(p) and os.path.exists(os.path.join(p, "Transactions.csv")):
                data_directory = p
                break

        if not data_directory:
            print(f"❌ Không tìm thấy thư mục chứa Transactions.csv trong: {candidate_paths}")
            sys.exit(1)

        res = run_eda_pipeline(data_dir=data_directory, output_img_dir=img_directory, debug=args.debug)

    # Lưu metrics nếu là full run
    if not args.debug:
        metrics_file = os.path.join(project_dir, "reports", ".eda_metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print(f"📁 Đã lưu số liệu tính toán chi tiết tại: {metrics_file}")
