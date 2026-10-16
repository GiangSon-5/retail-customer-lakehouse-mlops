"""
api/schemas.py
Pydantic Schemas định nghĩa cấu trúc dữ liệu Input và Output cho Production API.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    """Schema dữ liệu đầu vào phục vụ suy luận."""
    features: Dict[str, Any] = Field(
        ...,
        description="Dictionary chứa các đặc trưng đầu vào phục vụ mô hình",
        example={"feature_1": 10.5, "feature_2": "category_A"}
    )

class PredictionResponse(BaseModel):
    """Schema kết quả dự đoán trả về."""
    prediction: Any = Field(..., description="Nhãn hoặc giá trị dự đoán của mô hình")
    probability: Optional[float] = Field(None, description="Xác suất dự đoán (nếu là bài toán phân loại)")
    model_version: str = Field(..., description="Phiên bản mô hình đang phục vụ")
    latency_ms: float = Field(..., description="Độ trễ suy luận tính bằng mili-giây")

class HealthCheckResponse(BaseModel):
    """Schema kiểm tra sức khỏe dịch vụ."""
    status: str = Field(..., example="healthy")
    model_loaded: bool = Field(..., example=True)
    version: str = Field(..., example="1.0.0")
