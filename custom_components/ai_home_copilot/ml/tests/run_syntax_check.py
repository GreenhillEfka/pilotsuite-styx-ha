"""Standalone test for ML modules - no HA dependencies."""

import sys
import os
import ast

# Get the ml directory
ml_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(f"ML directory: {ml_dir}")


def validate_syntax(filepath: str) -> bool:
    """Validate Python syntax using ast.parse() instead of exec()."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code, filename=filepath)
        return True
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return False


# Test each module with safe syntax validation
test_files = [
    ("patterns/anomaly_detector.py", "AnomalyDetector"),
    ("patterns/habit_predictor.py", "HabitPredictor"),
    ("patterns/energy_optimizer.py", "EnergyOptimizer"),
    ("patterns/multi_user_learner.py", "MultiUserLearner"),
    ("training/__init__.py", "Training Pipeline"),
    ("inference/__init__.py", "Inference Engine"),
]

all_ok = True
for rel_path, name in test_files:
    filepath = os.path.join(ml_dir, rel_path)
    if os.path.exists(filepath):
        if validate_syntax(filepath):
            print(f"{name}: OK (syntax valid)")
        else:
            print(f"{name}: FAILED")
            all_ok = False
    else:
        print(f"{name}: SKIPPED (file not found)")

# Check ml_context.py
ml_context_path = os.path.join(os.path.dirname(ml_dir), "ml_context.py")
if os.path.exists(ml_context_path):
    if validate_syntax(ml_context_path):
        print("ML Context: OK (syntax valid)")
    else:
        print("ML Context: FAILED")
        all_ok = False

if all_ok:
    print("\n=== All ML modules syntax validated successfully! ===")
else:
    print("\n=== Some modules have syntax errors! ===")
    sys.exit(1)
