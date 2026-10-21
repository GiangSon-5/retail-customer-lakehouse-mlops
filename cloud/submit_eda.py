#!/usr/bin/env python3
"""
================================================================================
Module: cloud/submit_eda.py
Dự án: Retail Customer Segmentation & AWS Medallion Lakehouse
Mục tiêu:
    - Điều phối kích hoạt SageMaker Processing Job cho Trạm 3 (EDA Before Cleaning).
    - Tách biệt 100%: Nằm trong thư mục cloud/, không lẫn lộn với src/.
    - Sử dụng 'uv' để cài đặt dependencies siêu tốc (10-100x vs pip) trên Cloud Container.
    - Tự động đồng bộ 5 biểu đồ 300 DPI về reports/imgs/ và tự hủy máy sau khi chạy ($0 idle).
================================================================================
"""

import os
import sys
import time
import argparse
import boto3

# Thiết lập đường dẫn import module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    AWS_REGION,
    S3_BRONZE_BUCKET,
    SAGEMAKER_ROLE_ARN,
    SKLEARN_IMAGE_URI,
    DEFAULT_INSTANCE_TYPE,
    DEFAULT_INSTANCE_COUNT,
    DEFAULT_VOLUME_SIZE_GB,
    DEFAULT_MAX_RUNTIME_SECONDS,
)


def submit_eda_processing_job(debug: bool = False):
    print("=" * 80)
    print("🚀 [CLOUD RUNNER] SAGEMAKER PROCESSING JOB: TRẠM 3 (EDA BEFORE CLEANING)")
    print(f"🌍 AWS Region       : {AWS_REGION}")
    print(f"🪣 S3 Bronze Bucket : {S3_BRONZE_BUCKET}")
    print(f"🛡️ SageMaker Role   : {SAGEMAKER_ROLE_ARN}")
    print(f"📦 Container Image  : {SKLEARN_IMAGE_URI}")
    print(f"⚡ Package Manager  : uv (Astral Rust Package Manager - Ultra Fast)")
    print(f"⚙️ Chế độ thực thi  : {'--debug (Smoke Test 100 dòng)' if debug else 'Chạy Full 100% Lakehouse'}")
    print("=" * 80)

    s3 = boto3.client("s3", region_name=AWS_REGION)
    sm = boto3.client("sagemaker", region_name=AWS_REGION)

    # 1. Đẩy mã nguồn nghiệp vụ (src/eda_findings.py) và requirements.txt lên S3
    local_script_path = os.path.join(PROJECT_ROOT, "src", "eda_findings.py")
    local_req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    s3_code_prefix = "artifacts/code"

    print(f"\n[1/4] 📤 Đang đồng bộ mã nguồn & requirements.txt lên S3...")
    if not os.path.exists(local_script_path):
        raise FileNotFoundError(f"Không tìm thấy file mã nguồn tại {local_script_path}")

    s3.upload_file(local_script_path, S3_BRONZE_BUCKET, f"{s3_code_prefix}/eda_findings.py")
    print(f"      ✓ Đã upload: src/eda_findings.py -> s3://{S3_BRONZE_BUCKET}/{s3_code_prefix}/eda_findings.py")

    if os.path.exists(local_req_path):
        s3.upload_file(local_req_path, S3_BRONZE_BUCKET, f"{s3_code_prefix}/requirements.txt")
        print(f"      ✓ Đã upload: requirements.txt -> s3://{S3_BRONZE_BUCKET}/{s3_code_prefix}/requirements.txt")

    # 2. Khởi tạo Processing Job
    job_name = f"retail-eda-{int(time.time())}"
    container_args = [
        "--s3-bucket", S3_BRONZE_BUCKET,
        "--output-img-dir", "/opt/ml/processing/output/imgs"
    ]
    if debug:
        container_args.append("--debug")

    # Entrypoint chuyên nghiệp: Cài uv trước -> Dùng uv cài requirements.txt siêu tốc -> Chạy code
    container_entrypoint = [
        "bash", "-c",
        (
            "pip install --quiet uv && "
            "uv pip install --system --quiet -r /opt/ml/processing/input/code/requirements.txt && "
            "python3 /opt/ml/processing/input/code/eda_findings.py \"$@\""
        ),
        "--"
    ]

    print(f"\n[2/4] ☁️ Đang yêu cầu AWS SageMaker khởi tạo Processing Job: {job_name}...")
    sm.create_processing_job(
        ProcessingJobName=job_name,
        RoleArn=SAGEMAKER_ROLE_ARN,
        AppSpecification={
            "ImageUri": SKLEARN_IMAGE_URI,
            "ContainerEntrypoint": container_entrypoint,
            "ContainerArguments": container_args,
        },
        ProcessingInputs=[
            {
                "InputName": "code",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": f"s3://{S3_BRONZE_BUCKET}/{s3_code_prefix}/",
                    "LocalPath": "/opt/ml/processing/input/code",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        ],
        ProcessingOutputConfig={
            "Outputs": [
                {
                    "OutputName": "eda-plots",
                    "AppManaged": False,
                    "S3Output": {
                        "S3Uri": f"s3://{S3_BRONZE_BUCKET}/reports/imgs",
                        "LocalPath": "/opt/ml/processing/output/imgs",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        ProcessingResources={
            "ClusterConfig": {
                "InstanceCount": DEFAULT_INSTANCE_COUNT,
                "InstanceType": DEFAULT_INSTANCE_TYPE,
                "VolumeSizeInGB": DEFAULT_VOLUME_SIZE_GB,
            }
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": DEFAULT_MAX_RUNTIME_SECONDS
        },
        Tags=[
            {"Key": "Project", "Value": "retail-customer-lakehouse"},
            {"Key": "Stage", "Value": "03_EDA_Before_Cleaning"},
            {"Key": "Orchestrator", "Value": "cloud.submit_eda"}
        ]
    )
    print(f"      ✅ Job đã tạo thành công trên AWS! Đang chờ container khởi động...")

    # 3. Theo dõi tiến trình thời gian thực
    print(f"\n[3/4] ⏳ Đang theo dõi tiến trình chạy trên Cloud (AWS Compute)...")
    start_time = time.time()
    last_status = None
    while True:
        desc = sm.describe_processing_job(ProcessingJobName=job_name)
        status = desc["ProcessingJobStatus"]
        elapsed = int(time.time() - start_time)

        if status != last_status:
            print(f"      ⏱️ [{elapsed}s] Trạng thái Cloud: {status}")
            last_status = status

        if status == "Completed":
            print(f"\n🎉 [THÀNH CÔNG] SageMaker Processing Job đã hoàn thành trong {elapsed}s!")
            break
        elif status in ["Failed", "Stopped"]:
            failure_reason = desc.get("FailureReason", "Không rõ nguyên nhân")
            print(f"\n❌ [THẤT BẠI] Job kết thúc với trạng thái: {status}")
            print(f"   Nguyên nhân: {failure_reason}")
            try:
                logs_client = boto3.client("logs", region_name=AWS_REGION)
                events = logs_client.filter_log_events(
                    logGroupName="/aws/sagemaker/ProcessingJobs",
                    logStreamNamePrefix=job_name
                ).get("events", [])
                if events:
                    print("\n📜 [CHI TIẾT LỖI TỪ CLOUDWATCH]:")
                    for ev in events[-15:]:
                        print(f"   {ev['message'].strip()}")
            except Exception:
                pass
            sys.exit(1)

        time.sleep(15)

    # 4. Tự động đồng bộ các file ảnh kết quả từ S3 về máy Local
    local_report_dir = os.path.join(PROJECT_ROOT, "reports", "imgs")
    os.makedirs(local_report_dir, exist_ok=True)
    print(f"\n[4/4] 📥 Đang tải 5 biểu đồ kết quả từ S3 về máy Local ({local_report_dir})...")

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BRONZE_BUCKET, Prefix="reports/imgs/")
    download_count = 0
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".png"):
                filename = os.path.basename(key)
                local_path = os.path.join(local_report_dir, filename)
                s3.download_file(S3_BRONZE_BUCKET, key, local_path)
                print(f"      🖼️ Đã tải: {filename}")
                download_count += 1

    print("=" * 80)
    print(f"✅ HOÀN TẤT TRỌN VẸN: {download_count} biểu đồ 300 DPI đã có mặt tại reports/imgs/!")
    print("💰 Máy ảo SageMaker đã tự động hủy diệt ngay sau khi chạy xong ($0 chi phí tồn lưu).")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit SageMaker Processing Job from Local (Dedicated Cloud Runner)")
    parser.add_argument("--debug", action="store_true", help="Chạy thử nghiệm nhanh (Smoke Test) với 100 dòng")
    args = parser.parse_args()

    submit_eda_processing_job(debug=args.debug)
