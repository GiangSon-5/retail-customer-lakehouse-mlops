"""Module quan tri tai nguyen phan cung va khong che tran CPU <= 80%.

Su dung cho Production AI va MLOps pipelines de dam bao tai nguyen may chu / container
khong bi chiem dung doc quyen, giu he thong on dinh va mat me.
"""

import os
import sys
from typing import Dict, Any

def get_safe_n_jobs(max_pct: float = 0.75) -> int:
    """Tinh toan so luong worker an toan cho cac thu vien song song.

    Cong thuc: N_safe = max(1, floor(total_cores * max_pct))
    Duy tri CPU su dung trong khoang 70% - 80%, tranh qua tai he thong.

    Args:
        max_pct: Ty le tran tai nguyen CPU cho phep (mac dinh 0.75).

    Returns:
        So luong worker an toan de truyen vao n_jobs, thread_count, num_threads.
    """
    total_cores = os.cpu_count() or 4
    clamped_pct = min(max(max_pct, 0.1), 0.8)
    return max(1, int(total_cores * clamped_pct))

def configure_cpu_governor(max_pct: float = 0.75, set_priority: bool = True) -> int:
    """Thiet lap bien moi truong C-level runtime va ha do uu tien tien trinh.

    Nen goi o dong DAU TIEN cua script truoc khi import numpy/torch.

    Args:
        max_pct: Ty le tran tai nguyen CPU cho phep (mac dinh 0.75).
        set_priority: Co ha do uu tien tien trinh xuong BELOW_NORMAL hay khong.

    Returns:
        So luong luong tinh toan duoc cau hinh (safe_threads).
    """
    safe_threads = get_safe_n_jobs(max_pct=max_pct)
    str_threads = str(safe_threads)

    # 1. Khoa cac engine tinh toan cap thap (C/Fortran/BLAS/OpenMP)
    c_env_vars = [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ]
    for var in c_env_vars:
        os.environ[var] = str_threads

    # 2. Dong bo PyTorch thread pool neu da nạp
    if "torch" in sys.modules:
        try:
            import torch
            torch.set_num_threads(safe_threads)
        except Exception:
            pass

    # 3. Dong bo OpenCV thread pool neu da nap
    if "cv2" in sys.modules:
        try:
            import cv2
            cv2.setNumThreads(safe_threads)
        except Exception:
            pass

    # 4. Ha do uu tien tien trinh (Process Priority)
    if set_priority:
        try:
            import psutil
            p = psutil.Process()
            if sys.platform.startswith("win"):
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                current_nice = p.nice()
                p.nice(min(current_nice + 5, 19))
        except Exception:
            pass

    return safe_threads

def get_cpu_resource_report() -> Dict[str, Any]:
    """Bao cao thong so tai nguyen CPU hien tai."""
    total_logical = os.cpu_count() or 4
    safe_threads = get_safe_n_jobs(0.75)
    return {
        "total_logical_cores": total_logical,
        "recommended_safe_threads": safe_threads,
        "cpu_ceiling_percentage": "75%",
        "active_env_settings": {
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "Not Set"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "Not Set"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", "Not Set"),
        }
    }
