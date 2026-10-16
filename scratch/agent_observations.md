# SỔ TAY QUAN SÁT: KẾT QUẢ TERRAFORM PLAN THÀNH CÔNG (11 TÀI NGUYÊN) & LỆNH APPLY

> **Dự án**: AWS-Powered Customer Segmentation & ML Pipeline Platform  
> **Chặng**: Chặng 2 - Triển Khai Thực Tế Hạ Tầng S3 Lakehouse  
> **Tiến độ**: `terraform plan` ĐÃ THÀNH CÔNG XUẤT SẮC (**11 to add, 0 to change, 0 to destroy**)  
> **Tài khoản AWS đích**: Account ID `876760932342` | Region: `ap-southeast-1` | IAM User: `admin`  
> **Thời điểm cập nhật**: 2026-10-15  

---

## 1. PHÂN TÍCH KẾT QUẢ KẾ HOẠCH (PLAN AUDIT)
Bản kế hoạch Terraform vừa tạo đã bao hàm đầy đủ 11 chốt chặn chuẩn mực Enterprise:
- **3 Buckets S3 Medallion**: `bronze` (Landing), `silver` (Cleaned Parquet), `gold` (RFM Features).
- **3 Chốt chặn Public Access**: Khóa 100% quyền truy cập công khai ngoài Internet.
- **3 Cấu hình Mã hóa Tự động**: Bật mã hóa máy chủ AES256 bảo vệ dữ liệu lúc nghỉ (At-Rest Encryption).
- **1 Chuông báo tài chính**: CloudWatch Metric Alarm cảnh báo khi chi phí vượt ngưỡng 1.00 USD.
- **1 Sổ đăng bạ dữ liệu**: AWS Glue Catalog Database (`retail_customer_analytics`) phục vụ truy vấn Athena Serverless.

---

## 2. HÀNH ĐỘNG NGAY: CHẠY LỆNH APPLY TRÊN POWERSHELL

Hiện tại Bạn đang đứng sẵn ở thư mục `projects/customer_segmentation/infra`, Bạn hãy chạy lệnh sau để Terraform chính thức tạo 11 tài nguyên lên AWS:

```powershell
terraform apply -auto-approve
```

*(Thời gian chạy khoảng 15 - 20 giây. Khi hoàn tất, màn hình sẽ in ra các dòng Output màu xanh lá cùng tên 3 buckets S3)*.

---

## 3. BƯỚC TIẾP THEO: ĐẨY DỮ LIỆU THÔ VÀO S3 BRONZE

Ngay sau khi lệnh apply báo thành công, Bạn chạy khối lệnh sau để đưa 2 file dữ liệu nguồn vào S3 Bronze:

```powershell
cd ../../..

# 1. Upload Transactions.csv len S3 Bronze
aws s3 cp projects/customer_segmentation/data/raw/Du_lieu_cung_cap/Transactions.csv s3://retail-customer-lakehouse-876760932342-bronze/transactions/Transactions.csv

# 2. Upload Products_with_Categories.csv len S3 Bronze
aws s3 cp projects/customer_segmentation/data/raw/Du_lieu_cung_cap/Products_with_Categories.csv s3://retail-customer-lakehouse-876760932342-bronze/products/Products_with_Categories.csv

# 3. Kiem tra toan ven file tren S3 Bronze
aws s3 ls s3://retail-customer-lakehouse-876760932342-bronze --recursive --human-readable --summarize
```

---

## 4. KẾ HOẠCH BÀN GIAO TIẾP THEO CỦA AGENT
Ngay khi Bạn kiểm tra thấy 2 file đã nằm an toàn trên S3 Bronze:
1. Agent sẽ nâng cấp script `src/etl_pipeline.py` để hỗ trợ cờ đọc trực tiếp từ `s3://...-bronze`.
2. Pipeline sẽ tự động trích xuất các chỉ số RFM và ghi kết quả Parquet thẳng lên `s3://...-silver` và `s3://...-gold` trên Cloud AWS của Bạn!
