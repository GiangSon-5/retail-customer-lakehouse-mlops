# 📖 SỔ TAY VẬN HÀNH DỰ ÁN & BẢNG LỆNH THỰC THI (PROJECT RUNBOOK)
## 🛒 Retail Customer Segmentation — Modern Data Lakehouse on AWS & MLOps Pipeline

---

## 📑 MỤC LỤC LỆNH VẬN HÀNH
1. [Khảo sát Môi trường & Danh tính AWS](#1-khảo-sát-môi-trường--danh-tính-aws)
2. [Hạ tầng Đám mây dạng mã (Terraform IaC)](#2-hạ-tầng-đám-mây-dạng-mã-terraform-iac)
3. [Nạp Dữ Liệu Lên Tầng S3 Bronze (Data Ingestion)](#3-nạp-dữ-liệu-lên-tầng-s3-bronze-data-ingestion)
4. [Kiểm toán & Đối soát Dữ liệu trên S3](#4-kiểm-toán--đối-soát-dữ-liệu-trên-s3)
5. [Dây chuyền Data Science: Làm sạch & Trích xuất RFM](#5-dây-chuyền-data-science-làm-sạch--trích-xuất-rfm)
6. [Quy trình FinOps Dọn dẹp Tránh Mất Phí (Teardown)](#6-quy-trình-finops-dọn-dẹp-tránh-mất-phí-teardown)

---

## 1. KHẢO SÁT MÔI TRƯỜNG & DANH TÍNH AWS

### 1.1. Kiểm tra tài khoản AWS đang kết nối
```powershell
aws sts get-caller-identity
```
- **Mục đích**: Xác định Account ID, IAM User/Role và đảm bảo CLI đã xác thực thành công.

### 1.2. Kiểm tra môi trường Python Virtualenv
```powershell
& "C:\Users\Admin\Desktop\Kaggle\.venv\Scripts\python.exe" -c "import sys; print('Python venv:', sys.executable)" --debug
```

---

## 2. HẠ TẦNG ĐÁM MÂY DẠNG MÃ (TERRAFORM IAC)

> **Thư mục thực thi**: `projects/customer_segmentation/infra/`

```powershell
# Chuyển vào thư mục hạ tầng
cd C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\infra
```

### 2.1. Khởi tạo driver Terraform (Chỉ chạy 1 lần đầu)
```powershell
terraform init
```

### 2.2. Xem trước bản vẽ thi công (Dry-run, 100% an toàn, 0đ phí)
```powershell
terraform plan
```

### 2.3. Triển khai tạo thật 11 tài nguyên lên AWS
```powershell
terraform apply -auto-approve
```
- **Tài nguyên được tạo**: 3 S3 Buckets (Bronze, Silver, Gold), 3 khóa Public Access, 3 cấu hình mã hóa AES-256, 1 CloudWatch Alarm (1 USD), 1 AWS Glue Catalog Database.

### 2.4. Kiểm tra trạng thái các tài nguyên đang quản lý
```powershell
terraform state list
```

---

## 3. NẠP DỮ LIỆU LÊN TẦNG S3 BRONZE (DATA INGESTION)

> **Mã nguồn**: [`src/data_loader.py`](file:///C:/Users/Admin/Desktop/Kaggle/projects/customer_segmentation/src/data_loader.py)

```powershell
# Đứng tại thư mục gốc dự án
cd C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation
```

### 3.1. Chạy kiểm thử siêu nhẹ (Micro-sampling --debug, N=50 dòng)
```powershell
& "C:\Users\Admin\Desktop\Kaggle\.venv\Scripts\python.exe" "C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\src\data_loader.py" --debug
```
- **Mục đích**: Kiểm tra kết nối mạng, quyền ghi S3 và khớp byte mà không tốn tài nguyên máy.

### 3.2. Chạy nạp TOÀN BỘ dữ liệu thật từ POS lên S3 Bronze (Production Run)
```powershell
& "C:\Users\Admin\Desktop\Kaggle\.venv\Scripts\python.exe" "C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\src\data_loader.py"
```
- **Tệp tin tải lên**:
  - `Transactions.csv` (807.857 bytes) $\rightarrow$ `s3://retail-customer-lakehouse-876760932342-bronze/raw/Transactions.csv`
  - `Products_with_Categories.csv` (5.895 bytes) $\rightarrow$ `s3://retail-customer-lakehouse-876760932342-bronze/raw/Products_with_Categories.csv`
- **Tính năng nổi bật**: Tự động phát hiện Bronze Bucket, khóa trần CPU $\le 75\%$, tự động xác thực dung lượng byte 100%.

### 3.3. Lệnh dự phòng bằng AWS CLI trực tiếp (Fallback)
```powershell
aws s3 cp "C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\data\raw\Du_lieu_cung_cap" "s3://retail-customer-lakehouse-876760932342-bronze/raw/" --recursive
```

---

## 4. KIỂM TOÁN & ĐỐI SOÁT DỮ LIỆU TRÊN S3

### 4.1. Liệt kê danh sách các S3 Bucket đang hoạt động
```powershell
aws s3 ls
```

### 4.2. Xem các tệp tin bên trong tầng S3 Bronze
```powershell
aws s3 ls s3://retail-customer-lakehouse-876760932342-bronze/raw/
```

### 4.3. Kiểm tra chi tiết 1 tệp tin (Metadata & Byte Size)
```powershell
aws s3api head-object --bucket retail-customer-lakehouse-876760932342-bronze --key raw/Transactions.csv
```

---

## 5. DÂY CHUYỀN DATA SCIENCE: LÀM SẠCH & TRÍCH XUẤT RFM

> **Mã nguồn**: [`src/etl_pipeline.py`](file:///C:/Users/Admin/Desktop/Kaggle/projects/customer_segmentation/src/etl_pipeline.py)

### 5.1. Chạy thử nghiệm làm sạch & tính RFM micro-sampling (--debug)
```powershell
& "C:\Users\Admin\Desktop\Kaggle\.venv\Scripts\python.exe" "C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\src\etl_pipeline.py" --debug
```

### 5.2. Chạy toàn bộ dữ liệu (Local Controlled Run, CPU $\le 75\%$)
```powershell
& "C:\Users\Admin\Desktop\Kaggle\.venv\Scripts\python.exe" "C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\src\etl_pipeline.py"
```
- **Đầu ra**:
  - `data/processed/silver_transactions.parquet` (Dữ liệu giao dịch sạch tầng Silver)
  - `data/processed/gold_rfm_features.parquet` (Bảng đặc trưng RFM 3.898 khách hàng tầng Gold)
  - Báo cáo đối soát chất lượng dữ liệu bảo toàn 100% khách hàng.

---

## 6. QUY TRÌNH FINOPS DỌN DẸP TRÁNH MẤT PHÍ (TEARDOWN)

> **Áp dụng định kỳ kiểm toán vận hành hoặc khi hoàn tất chu kỳ chạy batch**

### 6.1. Xóa sạch 100% tài nguyên trên AWS (Cam kết 0đ chi phí qua đêm)
```powershell
cd C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\infra
terraform destroy -auto-approve
```
- **Kết quả**: Xóa toàn bộ 3 S3 Buckets, Glue Database, CloudWatch Alarm trong vòng 15 giây.

### 6.2. Sáng hôm sau mở lại hạ tầng trong 15 giây
```powershell
cd C:\Users\Admin\Desktop\Kaggle\projects\customer_segmentation\infra
terraform apply -auto-approve
```

---

## 7. RÀ SOÁT CHI PHÍ & DỊCH VỤ NGẦM TRÊN TERMINAL (FINOPS AUDIT)

### 7.1. Kiểm tra trạng thái chuông cảnh báo 1 USD
```powershell
aws cloudwatch describe-alarms --alarm-names "CustomerSegmentation-Spend-Alert-1USD" --query "MetricAlarms[].[AlarmName,StateValue,StateReason]" --output table
```

### 7.2. Kiểm tra chi tiết tiền tiêu từng dịch vụ trong tháng
```powershell
aws ce get-cost-and-usage --time-period Start=2026-10-01,End=2026-10-17 --granularity MONTHLY --metrics "UnblendedCost" --group-by Type=DIMENSION,Key=SERVICE --query "ResultsByTime[].Groups[].[Keys[0],Metrics.UnblendedCost.Amount]" --output table
```

### 7.3. Rà soát máy chủ EC2 đang chạy ngầm
```powershell
aws ec2 describe-instances --query "Reservations[].Instances[?State.Name=='running'].[InstanceId,InstanceType,LaunchTime]" --output table
```

### 7.4. Rà soát NAT Gateway (Nguy cơ tốn tiền ngầm cao nhất)
```powershell
aws ec2 describe-nat-gateways --query "NatGateways[?State=='available'].[NatGatewayId,VpcId]" --output table
```

### 7.5. Rà soát máy chủ SageMaker (Notebooks & Endpoints)
```powershell
aws sagemaker list-notebook-instances --query "NotebookInstances[?NotebookInstanceStatus=='InService'].NotebookInstanceName" --output table
aws sagemaker list-endpoints --query "Endpoints[?EndpointStatus=='InService'].EndpointName" --output table
```

### 7.6. Kiểm tra tổng dung lượng file thực tế trên S3 Bronze
```powershell
aws s3 ls s3://retail-customer-lakehouse-876760932342-bronze/raw/ --recursive --human-readable --summarize
```

