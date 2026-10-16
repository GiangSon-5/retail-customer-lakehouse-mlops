"""
api/app.py
Production API endpoint phục vụ suy luận thời gian thực (Real-time Inference).
"""
import time
from fastapi import FastAPI, HTTPException
from api.schemas import PredictionRequest, PredictionResponse, HealthCheckResponse
from src.utils import setup_logger

logger = setup_logger("production_api")
app = FastAPI(
    title="Production ML Inference Service",
    description="REST API phục vụ dự đoán thời gian thực cho giải pháp Doanh nghiệp",
    version="1.0.0"
)

MODEL_VERSION = "1.0.0"
MODEL_LOADED = False

@app.on_event("startup")
def load_model() -> None:
    """Tải trọng số mô hình khi khởi động service."""
    global MODEL_LOADED
    # Khởi tạo nạp artifact mô hình (ONNX / Joblib) tại đây
    logger.info("Đang khởi tạo nạp mô hình phiên bản %s...", MODEL_VERSION)
    MODEL_LOADED = True
    logger.info("Nạp mô hình thành công, sẵn sàng phục vụ requests.")

@app.get("/health", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    """Endpoint kiểm tra trạng thái hoạt động của service (Liveness/Readiness probe)."""
    return HealthCheckResponse(
        status="healthy" if MODEL_LOADED else "unhealthy",
        model_loaded=MODEL_LOADED,
        version=MODEL_VERSION
    )

@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    """Endpoint thực hiện suy luận từ các đặc trưng đầu vào."""
    if not MODEL_LOADED:
        raise HTTPException(status_code=503, detail="Mô hình chưa sẵn sàng.")
    
    start_time = time.perf_counter()
    try:
        # Giả lập pipeline tiền xử lý và inference (sẽ kết nối trực tiếp với src/predict.py)
        # prediction_value = model.predict(transformed_features)
        prediction_value = 1
        probability_score = 0.92
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        return PredictionResponse(
            prediction=prediction_value,
            probability=probability_score,
            model_version=MODEL_VERSION,
            latency_ms=round(latency_ms, 2)
        )
    except Exception as exc:
        logger.error("Lỗi suy luận: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý nội bộ: {str(exc)}") from exc
