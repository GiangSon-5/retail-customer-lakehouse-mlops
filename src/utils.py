"""
src/utils.py
Tiện ích hệ thống cho Production AI / MLOps: Cố định seed, đo thời gian thực thi, logging chuẩn hóa.
"""
import logging
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import numpy as np

def setup_logger(name: str = "production_app", level: int = logging.INFO) -> logging.Logger:
    """Khởi tạo logger theo chuẩn công nghiệp."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

def seed_everything(seed: int = 42) -> None:
    """Cố định seed ngẫu nhiên cho môi trường sản xuất có thể tái lập."""
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
    except ImportError:
        pass

@contextmanager
def timer(task_name: str, logger: logging.Logger = None) -> Generator[None, None, None]:
    """Context manager đo thời gian thực thi (Latency / Runtime)."""
    start_time = time.perf_counter()
    if logger:
        logger.info("Bắt đầu tác vụ: %s", task_name)
    else:
        print(f"[{task_name}] Bắt đầu...")
    yield
    elapsed = time.perf_counter() - start_time
    if logger:
        logger.info("Hoàn thành: %s trong %.4f giây (%.2f ms)", task_name, elapsed, elapsed * 1000)
    else:
        print(f"[{task_name}] Hoàn thành trong {elapsed:.4f}s ({elapsed*1000:.2f}ms)")

def get_project_root() -> Path:
    """Trả về đường dẫn gốc của thư mục dự án."""
    return Path(__file__).resolve().parent.parent
