from experiments.phase3_ma_stability import MA_WINDOWS, parameter_grid
import subprocess
import sys
from pathlib import Path


def test_ma_stability_grid_is_exactly_frozen_values():
    assert parameter_grid() == (150, 175, 200, 225, 250)
    assert len(set(MA_WINDOWS)) == 5


def test_phase3_direct_entrypoint_loads():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "experiments/phase3_ma_stability.py"), "--help"],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
