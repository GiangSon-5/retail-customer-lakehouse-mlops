# BẢN ĐẶC TẢ MÔ HÌNH HÓA TRỰC QUAN NGHIỆP VỤ & DÒNG CHẢY DỮ LIỆU (VISUAL BUSINESS PROCESS & DATA MODELS)

> **Dự án**: AWS-Powered Customer Segmentation & ML Pipeline Platform for Retail  
> **Mã hồ sơ**: `VISUAL-MODELS-CUST-SEGMENT-AWS-V2`  
> **Phiên bản**: `2.0`  
> **Trạng thái**: `APPROVED`  
> **Tham chiếu BRD/SRS**: `BRD-CUST-SEGMENT-AWS-V2`, `SRS-CUST-SEGMENT-AWS-V2`  
> **Tác giả (BA)**: Senior Technical BA & Visual Process Architect  
> **Người duyệt**: Head of Retail Marketing & Cloud Tech Lead  
> **Ngày phê duyệt**: 2026-10-15  

### Nhật ký Thay đổi Phiên bản (Revision History)
| Phiên bản | Ngày | Người sửa | Tóm tắt các thay đổi | Mục sửa đổi | Lý do |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `2.0` | 2026-10-15 | Senior BA | Khởi tạo đầy đủ 7 mô hình trực quan chuẩn mực: Use Case Diagram, BPMN As-Is vs To-Be Swimlane, Activity Diagram, DFD Level 0 & 1, Lakehouse ERD, Customer Lifecycle State Machine, và BI Dashboard Wireframe Mockup | Toàn bộ | Chuẩn hóa bộ hồ sơ trực quan hóa toàn diện phục vụ Stakeholder và Dev Team |

---

## 1. SƠ ĐỒ USE CASE TỔNG THỂ (SYSTEM USE CASE DIAGRAM)

Sơ đồ thể hiện toàn bộ các tác nhân (Actors) và mối quan hệ tương tác với các phân hệ chức năng trên nền tảng AWS:

```mermaid
flowchart LR
    %% ACTORS
    subgraph ACTORS ["CÁC TÁC NHÂN (ACTORS)"]
        MKT["fa:fa-user-tie Trưởng Phòng Marketing"]
        CS["fa:fa-headset Nhân Viên CSKH"]
        DE["fa:fa-database Data Engineer"]
        MLE["fa:fa-brain MLOps Engineer"]
        SCHED["fa:fa-clock EventBridge Scheduler"]
    end

    %% SYSTEM BOUNDARY
    subgraph SYS_BOUNDARY ["NỀN TẢNG PHÂN KHÚC KHÁCH HÀNG & MLOPS (AWS RETAIL PLATFORM)"]
        UC01["UC-01: Tải tệp giao dịch lên S3 Bronze"]
        UC02["UC-02: Kích hoạt PySpark ETL làm sạch & tính RFM"]
        UC03["UC-03: Đóng gói Docker Container qua CodeBuild"]
        UC04["UC-04: Huấn luyện K-Means với Spot Instance"]
        UC05["UC-05: Suy luận Batch Transform gán nhãn phân khúc"]
        UC06["UC-06: Truy vấn danh sách VIP / At-Risk trên Athena"]
        UC07["UC-07: Xuất danh sách gửi Voucher cá nhân hóa"]
        UC08["UC-08: Giám sát State Machine & Cảnh báo Ngân sách"]
        UC09["UC-09: Tự động dọn dẹp tài nguyên (Teardown)"]
    end

    %% RELATIONSHIPS
    DE --> UC01
    SCHED --> UC02
    DE --> UC02
    MLE --> UC03
    MLE --> UC04
    SCHED --> UC05
    MKT --> UC06
    MKT --> UC07
    CS --> UC07
    DE --> UC08
    DE --> UC09

    UC02 -.->|<<include>>| UC01
    UC05 -.->|<<include>>| UC04
    UC07 -.->|<<include>>| UC06
```

---

## 2. QUY TRÌNH NGHIỆP VỤ BPMN 2.0 PHÂN LÀN (SWIMLANE WORKFLOW: AS-IS VS TO-BE)

### 2.1 Quy Trình Hiện Trạng (As-Is: Thủ Công, Chậm Trễ & Thất Thoát)
Hiện tại, dữ liệu nằm rời rạc trong các file Excel/CSV máy cá nhân. Tiếp thị dàn trải gửi cùng một thông điệp cho toàn bộ khách hàng:

```mermaid
flowchart TD
    subgraph POS_STORE ["CỬA HÀNG / BÁN LẺ"]
        A1["Khách hàng mua hàng tại quầy"] --> A2["Thu ngân quét mã & in hóa đơn"]
        A2 --> A3["Hệ thống POS xuất file CSV cuối tuần"]
    end

    subgraph MANUAL_MKT ["PHÒNG MARKETING (THỦ CÔNG)"]
        A3 -->|Gửi email đính kèm| B1["Nhân viên tải file CSV về Excel"]
        B1 --> B2["Lọc thủ công bằng mắt / filter cơ bản"]
        B2 --> B3["Soạn tin nhắn SMS khuyến mãi chung"]
        B3 --> B4["Bắn tin nhắn SMS Brandname hàng loạt<br/><i>(Tốn 450 VND/tin x 20.000 khách)</i>"]
    end

    subgraph CUSTOMER_EXP ["TRẢI NGHIỆM KHÁCH HÀNG"]
        B4 --> C1{"Khách hàng phản ứng"}
        C1 -->|VIP cảm thấy bị spam| C2["Khó chịu, bỏ qua tin nhắn"]
        C1 -->|Khách At-Risk không có ưu đãi kéo lại| C3["Rời bỏ sang cửa hàng đối thủ"]
    end
```

### 2.2 Quy Trình Tương Lai (To-Be: Tự Động Hóa 100% trên AWS Cloud Data Lakehouse)

```mermaid
flowchart TD
    subgraph LANE_POS ["1. NGUỒN DỮ LIỆU BÁN HÀNG"]
        T1["Giao dịch phát sinh"] --> T2["Batch Export định kỳ tự động"]
    end

    subgraph LANE_AWS_DATA ["2. HỒ DỮ LIỆU & PYSPARK ETL (AWS DATA LAKE)"]
        T2 -->|S3 Upload Event| T3["S3 Bronze Bucket"]
        T3 --> T4["AWS Glue / PySpark Job<br/><i>(Làm sạch, Join danh mục, tính RFM)</i>"]
        T4 --> T5["S3 Silver (Cleaned) & Gold (RFM Features)"]
    end

    subgraph LANE_AWS_MLOPS ["3. HỌC MÁY & MLOPS (AMAZON SAGEMAKER)"]
        T5 --> T6["SageMaker Managed Spot Training<br/><i>(Tối ưu K-Means & Silhouette)</i>"]
        T6 --> T7["SageMaker Batch Transform<br/><i>(Gán nhãn 5 phân khúc định kỳ)</i>"]
        T7 --> T8["S3 Gold / customer_rfm_segments"]
    end

    subgraph LANE_SERVING ["4. PHỤC VỤ TRUY VẤN (GLUE CATALOG & ATHENA)"]
        T8 --> T9["Glue Catalog Update"]
        T9 --> T10["Amazon Athena SQL Mart"]
    end

    subgraph LANE_MARKETING ["5. PHÒNG MARKETING & CHĂM SÓC KHÁCH HÀNG"]
        T10 --> T11["BI Dashboard tự động cập nhật"]
        T11 --> T12{"Hành động theo phân khúc"}
        T12 -->|Champions / VIP| T13["Tặng voucher độc quyền sinh nhật"]
        T12 -->|At Risk| T14["Kích hoạt chiến dịch kéo lại khẩn cấp"]
        T12 -->|Promising| T15["Gợi ý combo kích cầu lần mua thứ 2"]
    end
```

---

## 3. SƠ ĐỒ HOẠT ĐỘNG CHI TIẾT (ACTIVITY DIAGRAM VỚI CÁC ĐIỀU KIỆN RẼ NHÁNH)

Sơ đồ mô tả chi tiết logic điều kiện, kiểm tra lỗi và rẽ nhánh từ lúc dữ liệu thô vào đến khi xuất báo cáo:

```mermaid
flowchart TD
    START([Bắt đầu Pipeline]) --> INGEST[Nhận tệp dữ liệu thô tại S3 Bronze]
    
    INGEST --> CHECK_FILE{Tệp có hợp lệ<br/>& có dữ liệu không?}
    CHECK_FILE -- Không --> ERR_ALERT[Gửi SNS cảnh báo lỗi file & Dừng Pipeline]
    ERR_ALERT --> END_FAIL([Kết thúc lỗi])
    
    CHECK_FILE -- Có --> CLEAN[PySpark: Đọc dữ liệu & chuẩn hóa kiểu Date ISO]
    CLEAN --> JOIN_PROD[PySpark: Join với bảng Products]
    
    JOIN_PROD --> CHECK_PRICE{Phát hiện giá sản phẩm<br/>bị thiếu / null?}
    CHECK_PRICE -- Có --> IMPUTE_MEDIAN[Điền giá trung vị theo Category & ghi log]
    CHECK_PRICE -- Không --> COMPUTE_RFM[Tính toán chỉ số R, F, M per Member]
    IMPUTE_MEDIAN --> COMPUTE_RFM
    
    COMPUTE_RFM --> SCALE[StandardScaler chuẩn hóa đặc trưng]
    SCALE --> WRITE_GOLD[Ghi bảng rfm_features vào S3 Gold dạng Parquet]
    
    WRITE_GOLD --> SM_TRAIN[Kích hoạt SageMaker Training với Spot Instance]
    SM_TRAIN --> EVAL_SILHOUETTE{Silhouette Score<br/>>= 0.55?}
    
    EVAL_SILHOUETTE -- Không đạt --> ADJUST_K[Thử nghiệm K lân cận K in 3..8]
    ADJUST_K --> SM_TRAIN
    
    EVAL_SILHOUETTE -- Đạt --> SAVE_MODEL[Lưu model.tar.gz vào S3 Registry]
    SAVE_MODEL --> BATCH_TRANSFORM[Thực thi SageMaker Batch Transform gán nhãn cụm]
    
    BATCH_TRANSFORM --> APPLY_RULES[Áp dụng quy tắc BR-03 gán nhãn kinh doanh 5 phân khúc]
    APPLY_RULES --> WRITE_SEGMENTS[Ghi customer_rfm_segments vào S3 Gold]
    
    WRITE_SEGMENTS --> RECONCILE{Đối soát số lượng:<br/>Count Gold == 3.898?}
    RECONCILE -- Không --> FLAG_ANOMALY[Đánh dấu cảnh báo Data Loss & rà soát]
    RECONCILE -- Khớp 100% --> UPDATE_ATHENA[Cập nhật Metadata Glue Catalog]
    
    FLAG_ANOMALY --> UPDATE_ATHENA
    UPDATE_ATHENA --> SEND_SUCCESS[Gửi thông báo thành công qua Amazon SNS]
    SEND_SUCCESS --> END_SUCCESS([Hoàn tất Pipeline])
```

---

## 4. SƠ ĐỒ DÒNG CHẢY DỮ LIỆU (DATA FLOW DIAGRAM - DFD LEVEL 0 & LEVEL 1)

### 4.1 DFD Level 0 (Context Diagram - Bối Cảnh Hệ Thống)

```mermaid
flowchart LR
    POS[Hệ Thống Thu Ngân POS / Bán Hàng] -->|Giao dịch thô & Danh mục sản phẩm| SYS((HỆ THỐNG PHÂN KHÚC KHÁCH HÀNG & MLOPS TRÊN AWS))
    SYS -->|Danh sách VIP & At-Risk cá nhân hóa| MKT_DEPT[Bộ Phận Marketing & Tiếp Thị]
    SYS -->|Báo cáo doanh thu & Phân bố sức mua| EXEC[Ban Giám Đốc Bán Lẻ]
    SYS -->|Cảnh báo vận hành & Giám sát chi phí| OPS[Kỹ Sư Vận Hành & FinOps]
```

### 4.2 DFD Level 1 (Phân Rã Tiến Trình Xử Lý & Kho Dữ Liệu)

```mermaid
flowchart TD
    %% EXTERNAL ENTITIES
    POS[Hệ Thống POS]
    MKT[Bộ Phận Marketing]

    %% DATA STORES
    D1[(D1: S3 Bronze - Raw Data)]
    D2[(D2: S3 Silver - Cleaned Parquet)]
    D3[(D3: S3 Gold - RFM Features)]
    D4[(D4: S3 Gold - Customer Segments)]
    D5[(D5: S3 Model Registry)]

    %% PROCESSES
    P1["1.0 Tiếp Nhận & Lưu Trữ Thô"]
    P2["2.0 Làm Sạch & Trích Xuất RFM (PySpark)"]
    P3["3.0 Huấn Luyện K-Means (SageMaker)"]
    P4["4.0 Suy Luận Phân Cụm Batch"]
    P5["5.0 Phục Vụ Truy Vấn & Báo Cáo (Athena)"]

    POS -->|Tệp CSV giao dịch| P1
    P1 -->|Lưu trữ nguyên bản| D1

    D1 -->|Đọc raw data| P2
    P2 -->|Ghi dữ liệu giao dịch sạch| D2
    P2 -->|Ghi đặc trưng RFM đã scale| D3

    D3 -->|Đọc đặc trưng huấn luyện| P3
    P3 -->|Lưu artifact model.tar.gz| D5

    D5 & D3 -->|Tải model & đặc trưng| P4
    P4 -->|Ghi kết quả phân cụm| D4

    D4 -->|Đọc dữ liệu phân khúc| P5
    P5 -->|Xuất danh sách khách hàng & BI Dashboard| MKT
```

---

## 5. MÔ HÌNH DỮ LIỆU QUAN HỆ & THỰC THỂ LAKEHOUSE (ERD)

Sơ đồ mô tả cấu trúc quan hệ giữa các bảng từ tầng Bronze qua Silver đến Gold:

```mermaid
erDiagram
    BRONZE_TRANSACTIONS {
        string Member_number "Mã khách hàng thô"
        string Date "Ngày mua DD-MM-YYYY"
        string productId "Mã sản phẩm"
        string Items "Mô tả sản phẩm"
    }

    BRONZE_PRODUCTS {
        string productId "Mã sản phẩm"
        string productName "Tên sản phẩm"
        string Category "Ngành hàng"
        float Price "Đơn giá niêm yết"
    }

    SILVER_TRANSACTIONS {
        string member_number PK "Mã khách hàng chuẩn"
        date transaction_date "Ngày giao dịch YYYY-MM-DD"
        int year "Năm phân vùng"
        int month "Tháng phân vùng"
        string product_id "Mã sản phẩm"
        string product_name "Tên sản phẩm"
        string category "Ngành hàng"
        decimal unit_price "Đơn giá đã xử lý"
        int quantity "Số lượng mua"
        decimal line_total_amount "Tổng tiền dòng hàng"
    }

    GOLD_RFM_FEATURES {
        string member_number PK "Mã khách hàng duy nhất"
        int recency_days "Số ngày từ lần mua cuối"
        int frequency_count "Tổng số ngày mua"
        decimal monetary_total "Tổng tiền chi tiêu"
        float r_scaled "Đặc trưng R chuẩn hóa"
        float f_scaled "Đặc trưng F chuẩn hóa"
        float m_scaled "Đặc trưng M chuẩn hóa"
    }

    GOLD_CUSTOMER_SEGMENTS {
        string member_number PK "Mã khách hàng duy nhất"
        int recency_days "Số ngày từ lần mua cuối"
        int frequency_count "Tổng số ngày mua"
        decimal monetary_total "Tổng tiền chi tiêu"
        int r_score "Điểm R (1-4)"
        int f_score "Điểm F (1-4)"
        int m_score "Điểm M (1-4)"
        string rfm_class "Chuỗi RFM (vd: 444)"
        int cluster_id "Cụm K-Means (0-4)"
        string segment_name "Tên phân khúc BR-03"
        string marketing_action "Hành động tiếp thị khuyến nghị"
        string model_version "Phiên bản mô hình"
        timestamp processed_at "Thời điểm cập nhật"
    }

    BRONZE_TRANSACTIONS ||--o{ SILVER_TRANSACTIONS : "Cleansed & Enriched"
    BRONZE_PRODUCTS ||--o{ SILVER_TRANSACTIONS : "Joined on productId"
    SILVER_TRANSACTIONS ||--|| GOLD_RFM_FEATURES : "Aggregated per Member"
    GOLD_RFM_FEATURES ||--|| GOLD_CUSTOMER_SEGMENTS : "Clustered & Segmented"
```

---

## 6. SƠ ĐỒ MÁY TRẠNG THÁI VÒNG ĐỜI KHÁCH HÀNG (CUSTOMER LIFECYCLE STATE MACHINE)

Sơ đồ mô tả quy luật biến chuyển giữa các trạng thái khách hàng theo thời gian và hành vi chi tiêu:

```mermaid
stateDiagram-v2
    [*] --> NewCustomer: Giao dịch đầu tiên phát sinh
    
    NewCustomer --> Promising: Recency <= 30 ngày, Frequency <= 2, Monetary < 500k
    NewCustomer --> LoyalCustomers: Mua lại nhiều lần, F >= 5, M >= 1.5 triệu
    
    Promising --> LoyalCustomers: Tần suất mua tăng đều đặn (F >= 4)
    Promising --> Lost: Không quay lại sau 90 ngày (R > 90)
    
    LoyalCustomers --> Champions: Chi tiêu hàng đầu, mua liên tục (R <= 15, F >= 8, M >= 3 triệu)
    Champions --> LoyalCustomers: Giảm nhẹ tần suất nhưng vẫn mua đều
    
    LoyalCustomers --> AtRisk: Quá 45 ngày không phát sinh giao dịch mới (R >= 45)
    Champions --> AtRisk: Quá 45 ngày không mua hàng (Nguy cơ mất VIP)
    
    AtRisk --> LoyalCustomers: Kích hoạt thành công bằng Voucher (Quay lại mua)
    AtRisk --> Lost: Quá 90 ngày không phản hồi chiến dịch kéo lại (R > 90)
    
    Lost --> ReActivated: Khách hàng cũ quay lại mua sắm sau chiến dịch tái kích hoạt
    ReActivated --> Promising: Tiếp tục nuôi dưỡng
    Lost --> [*]: Khách hàng ngưng sử dụng dịch vụ vĩnh viễn
```

---

## 7. BẢN VẼ BỐ CỤC GIAO DIỆN BẢNG ĐIỀU KHIỂN (BI DASHBOARD WIREFRAME MOCKUP)

Bản vẽ thiết kế khung nhìn trực quan (Wireframe Mockup) cho Bảng điều khiển Phân khúc Khách hàng phục vụ Giám đốc Bán lẻ và Trưởng phòng Marketing:

```mermaid
flowchart TD
    subgraph HEADER ["KHUNG ĐIỀU KHIỂN CHUNG (HEADER & FILTER BAR)"]
        H1["LOGO: RETAIL CUSTOMER INSIGHTS"] --- H2["Bộ lọc: Khoảng thời gian [2014-2015 v]"]
        H2 --- H3["Bộ lọc: Ngành hàng [Tất cả v]"]
        H3 --- H4["Nút bấm: [Tải lại số liệu] [Xuất file Marketing CSV]"]
    end

    subgraph KPI_ROW ["HÀNG THẺ CHỈ SỐ CỐT LÕI (TOP KPI CARDS)"]
        K1["TỔNG KHÁCH HÀNG<br/><b>3.898</b><br/><i>(100% Khớp đối soát)</i>"]
        K2["DOANH SỐ VIP (CHAMPIONS)<br/><b>412.500.000 VND</b><br/><i>(Đóng góp 38.5% doanh thu)</i>"]
        K3["KHÁCH CẦN CỨU (AT-RISK)<br/><b>684 Khách</b><br/><i>(Doanh thu tiềm năng 120M)</i>"]
        K4["GIÁ TRỊ GIỎ HÀNG TB (AOV)<br/><b>215.000 VND</b><br/><i>(+16.2% so với kỳ trước)</i>"]
    end

    subgraph CHARTS_ROW ["HÀNG BIỂU ĐỒ TRỰC QUAN HÓA (VISUAL ANALYTICS)"]
        C1["BIỂU ĐỒ PHÂN BỐ CỤM RFM (SCATTER PLOT)<br/>----------------------------------------<br/>|  [VIP Champions]     * * * *         |<br/>|                         * *          |<br/>|  [Loyal]        o o o                |<br/>|  [At Risk]   x x x                   |<br/>|  [Lost]    . . .                     |<br/>----------------------------------------<br/>Trục hoành: Recency | Trục tung: Monetary"]
        
        C2["TỶ TRỌNG PHÂN KHÚC (DONUT CHART)<br/>----------------------------------------<br/>|   👑 Champions: 18.5%                |<br/>|   💎 Loyal Customers: 26.2%           |<br/>|   🌱 Promising / New: 21.0%          |<br/>|   ⚠️ At Risk: 17.5%                   |<br/>|   ❄️ Lost / Hibernating: 16.8%        |<br/>----------------------------------------"]
    end

    subgraph ACTION_TABLE ["DANH SÁCH KHÁCH HÀNG THEO HÀNH ĐỘNG TIẾP THỊ (ACTIONABLE LIST)"]
        T_GRID["| Mã KH | Phân Khúc | Lần Mua Cuối (R) | Tần Suất (F) | Tổng Chi Tiêu (M) | Hành Động Đề Xuất | Thao Tác |<br/>| :--- | :--- | :---: | :---: | :---: | :--- | :---: |<br/>| #1001 | 👑 Champions | 3 ngày trước | 14 lần | 3.850.000 VND | Tặng quà tri ân VIP | [Gửi Voucher VIP] |<br/>| #1042 | ⚠️ At Risk | 68 ngày trước | 8 lần | 2.150.000 VND | Kích hoạt mã giảm 20% | [Gửi SMS Cứu Khách]|<br/>| #1105 | 🌱 Promising | 5 ngày trước | 2 lần | 420.000 VND | Gợi ý combo gia đình | [Gửi Email Giới Thiệu]|"]
    end

    HEADER --> KPI_ROW
    KPI_ROW --> CHARTS_ROW
    CHARTS_ROW --> ACTION_TABLE
```
