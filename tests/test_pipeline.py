"""
tests/test_pipeline.py
Smoke test kiem tra tinh toan ven cua API va Utility trong du an san xuat.
"""
from pathlib import Path
from src.utils import get_project_root, seed_everything

def test_project_root() -> None:
    root = get_project_root()
    assert isinstance(root, Path)
    assert root.exists()

def test_seed_reproducibility() -> None:
    seed_everything(42)
    import numpy as np
    val_1 = np.random.rand()
    seed_everything(42)
    val_2 = np.random.rand()
    assert val_1 == val_2
