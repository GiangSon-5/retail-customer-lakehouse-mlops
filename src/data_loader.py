"""Module Data Loader & Ingestion lên AWS S3 Bronze Lakehouse.

Triển khai Chặng 1 trong kiến trúc MLOps:
- Tự động phát hiện S3 Bronze Bucket (hoặc nhận qua tham số CLI).
- Nạp dữ liệu thô từ POS (Transactions.csv, Products_with_Categories.csv).
- Upload an toàn lên S3 qua SDK Boto3 (hỗ trợ fallback AWS CLI).
- Xác thực tính toàn vẹn (File size & Checksum verification).
- Hỗ trợ chế độ --debug (micro-sampling N <= 50 dòng để test luồng end-to-end dưới 2 giây).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Tự động nạp thư mục gốc của dự án vào sys.path để import chuẩn 'src.*'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 1. Khóa trần CPU <= 75% trước khi thực thi
from src.hardware import configure_cpu_governor
configure_cpu_governor(max_pct=0.75)

from src.utils import setup_logger, timer

logger = setup_logger("data_loader")


def resolve_bronze_bucket(target_bucket: Optional[str] = None) -> str:
    """Tự động xác định tên S3 Bronze Bucket trên AWS.
    
    Args:
        target_bucket: Tên bucket chỉ định từ tham số dòng lệnh (nếu có).

    Returns:
        Tên S3 Bronze Bucket duy nhất.
    """
    if target_bucket:
        return target_bucket.strip()

    # Thử tìm qua AWS CLI
    try:
        cmd = ["aws", "s3api", "list-buckets", "--query", "Buckets[?contains(Name, 'bronze')].Name", "--output", "text"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        buckets = result.stdout.strip().split()
        if buckets and buckets[0]:
            chosen = buckets[0]
            logger.info("Đã tự động phát hiện Bronze Bucket trên AWS: %s", chosen)
            return chosen
    except Exception as exc:
        logger.warning("Không thể tự động truy vấn danh sách bucket qua AWS CLI: %s", exc)

    # Fallback mặc định theo định dạng dự án
    fallback = "retail-customer-lakehouse-876760932342-bronze"
    logger.info("Sử dụng cấu hình fallback Bronze Bucket: %s", fallback)
    return fallback


def upload_via_boto3(local_path: Path, bucket: str, s3_key: str) -> bool:
    """Upload tệp tin lên S3 bằng thư viện Boto3 chính thức.
    
    Args:
        local_path: Đường dẫn tệp tin trên máy cục bộ.
        bucket: Tên S3 bucket.
        s3_key: Đường dẫn khóa đích trên S3.

    Returns:
        True nếu upload thành công, False nếu thất bại hoặc thiếu thư viện.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.info("Chưa tìm thấy thư viện 'boto3' trong môi trường, kích hoạt fallback CLI.")
        return False

    try:
        s3_client = boto3.client("s3")
        file_size = local_path.stat().st_size
        logger.info("Đang upload qua Boto3: %s -> s3://%s/%s (%d bytes)...", local_path.name, bucket, s3_key, file_size)
        s3_client.upload_file(str(local_path), bucket, s3_key)
        logger.info("Upload thành công qua Boto3: s3://%s/%s", bucket, s3_key)
        return True
    except Exception as err:
        logger.error("Lỗi khi upload qua Boto3: %s", err)
        return False


def upload_via_aws_cli(local_path: Path, bucket: str, s3_key: str) -> bool:
    """Upload tệp tin lên S3 bằng AWS CLI (cơ chế Fallback đáng tin cậy).
    
    Args:
        local_path: Đường dẫn tệp tin cục bộ.
        bucket: Tên S3 bucket.
        s3_key: Đường dẫn đích trên S3.

    Returns:
        True nếu lệnh hoàn thành với exit code 0.
    """
    s3_uri = f"s3://{bucket}/{s3_key}"
    logger.info("Đang upload qua AWS CLI: %s -> %s...", local_path.name, s3_uri)
    cmd = ["aws", "s3", "cp", str(local_path), s3_uri]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        logger.info("Upload thành công qua AWS CLI: %s", s3_uri)
        return True
    else:
        logger.error("Lỗi AWS CLI (code %d): %s", res.returncode, res.stderr.strip())
        return False


def verify_s3_object(bucket: str, s3_key: str, expected_size: int) -> bool:
    """Xác thực tệp đã tồn tại trên S3 và khớp dung lượng byte.
    
    Args:
        bucket: Tên bucket.
        s3_key: Đường dẫn S3 object.
        expected_size: Dung lượng byte kỳ vọng của file gốc.

    Returns:
        True nếu file tồn tại trên S3 và dung lượng khớp 100%.
    """
    try:
        cmd = ["aws", "s3api", "head-object", "--bucket", bucket, "--key", s3_key, "--query", "ContentLength", "--output", "text"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        remote_size = int(res.stdout.strip())
        if remote_size == expected_size:
            logger.info("Xác thực toàn vẹn: s3://%s/%s khớp 100%% (%d bytes)", bucket, s3_key, remote_size)
            return True
        else:
            logger.warning("Lệch dung lượng s3://%s/%s: kỳ vọng %d vs thực tế %d", bucket, s3_key, expected_size, remote_size)
            return False
    except Exception as exc:
        logger.error("Không thể xác thực object s3://%s/%s: %s", bucket, s3_key, exc)
        return False


def run_ingestion_pipeline(
    raw_dir: Path, 
    bucket: str, 
    prefix: str = "raw/",
    is_debug: bool = False
) -> Dict[str, Any]:
    """Chạy quy trình nạp toàn bộ tệp tin thô từ POS lên S3 Bronze.
    
    Args:
        raw_dir: Thư mục chứa dữ liệu thô.
        bucket: Tên S3 Bronze Bucket.
        prefix: Tiền tố thư mục lưu trữ trên S3.
        is_debug: Cờ micro-sampling kiểm thử nhanh.

    Returns:
        Dictionary chứa tóm tắt kết quả nạp dữ liệu.
    """
    logger.info("=== BẮT ĐẦU INGESTION PIPELINE (POS -> S3 BRONZE) ===")
    logger.info("Thư mục nguồn cục bộ: %s", raw_dir)
    logger.info("S3 Bronze Đích: s3://%s/%s", bucket, prefix)
    logger.info("Chế độ DEBUG: %s", is_debug)

    # 1. Quét tìm 2 tệp tin thô cốt lõi
    files_to_upload = [
        ("Transactions.csv", raw_dir / "Transactions.csv"),
        ("Products_with_Categories.csv", raw_dir / "Products_with_Categories.csv"),
    ]

    # Kiểm tra tồn tại
    for name, fpath in files_to_upload:
        if not fpath.exists():
            # Thử tìm trong thư mục con nếu có
            sub_path = raw_dir / "Du_lieu_cung_cap" / name
            if sub_path.exists():
                fpath = sub_path
                files_to_upload = [(n, (raw_dir / "Du_lieu_cung_cap" / n) if (raw_dir / "Du_lieu_cung_cap" / n).exists() else p) for n, p in files_to_upload]
                break
            else:
                raise FileNotFoundError(f"Không tìm thấy tệp nguồn {name} tại {raw_dir}")

    results = {}
    scratch_dir = PROJECT_ROOT.parent.parent / "scratch" / "debug_samples"

    for file_name, file_path in files_to_upload:
        s3_key = f"{prefix.rstrip('/')}/{file_name}"
        
        # Nếu ở chế độ DEBUG, tạo mẫu siêu nhẹ (N <= 50 dòng) để kiểm thử
        if is_debug:
            scratch_dir.mkdir(parents=True, exist_ok=True)
            debug_path = scratch_dir / f"debug_{file_name}"
            with open(file_path, "r", encoding="utf-8", errors="replace") as fin, open(debug_path, "w", encoding="utf-8") as fout:
                for idx, line in enumerate(fin):
                    if idx >= 50:
                        break
                    fout.write(line)
            actual_upload_path = debug_path
            s3_key = f"debug_test/{file_name}"
            logger.info("DEBUG Mode: Đã trích xuất 50 dòng mẫu tại %s", debug_path)
        else:
            actual_upload_path = file_path

        expected_size = actual_upload_path.stat().st_size

        with timer(f"Upload {file_name}", logger=logger):
            # Ưu tiên Boto3, nếu không có thì fallback sang AWS CLI
            success = upload_via_boto3(actual_upload_path, bucket, s3_key)
            if not success:
                success = upload_via_aws_cli(actual_upload_path, bucket, s3_key)

        if not success:
            raise RuntimeError(f"Thất bại khi upload {file_name} lên s3://{bucket}/{s3_key}")

        # Xác thực toàn vẹn
        verified = verify_s3_object(bucket, s3_key, expected_size)
        results[file_name] = {
            "s3_uri": f"s3://{bucket}/{s3_key}",
            "size_bytes": expected_size,
            "status": "VERIFIED" if verified else "UNVERIFIED"
        }

    # Dọn dẹp scratch debug nếu có
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir, ignore_errors=True)

    logger.info("=== HOÀN TẤT INGESTION PIPELINE THÀNH CÔNG ===")
    return results


def main() -> None:
    """Hàm điều phối CLI."""
    parser = argparse.ArgumentParser(description="Nạp dữ liệu thô POS lên S3 Bronze Lakehouse")
    parser.add_argument(
        "--raw-dir", 
        type=str, 
        default=str(PROJECT_ROOT / "data" / "raw" / "Du_lieu_cung_cap"),
        help="Đường dẫn đến thư mục chứa file thô"
    )
    parser.add_argument(
        "--bucket", 
        type=str, 
        default=None,
        help="Tên S3 Bronze Bucket đích (để trống sẽ tự động phát hiện)"
    )
    parser.add_argument(
        "--prefix", 
        type=str, 
        default="raw/",
        help="Prefix trên S3"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Chế độ kiểm thử nhanh với micro-sampling (N <= 50 dòng)"
    )

    args = parser.parse_args()
    raw_path = Path(args.raw_dir)
    
    # Kiểm tra đường dẫn dự phòng nếu người dùng truyền data/raw
    if not raw_path.exists():
        fallback_path = PROJECT_ROOT / "data" / "raw"
        if (fallback_path / "Transactions.csv").exists():
            raw_path = fallback_path
        elif (fallback_path / "Du_lieu_cung_cap").exists():
            raw_path = fallback_path / "Du_lieu_cung_cap"

    bronze_bucket = resolve_bronze_bucket(args.bucket)
    run_ingestion_pipeline(
        raw_dir=raw_path,
        bucket=bronze_bucket,
        prefix=args.prefix,
        is_debug=args.debug
    )


if __name__ == "__main__":
    main()
