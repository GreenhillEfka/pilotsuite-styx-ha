"""Standalone test for ML modules - no HA dependencies."""

import sys
import os

# Get the ml directory
ml_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(f"ML directory: {ml_dir}")

# Test by executing each module directly
print("\n=== Testing AnomalyDetector ===")
exec(open(os.path.join(ml_dir, "patterns", "anomaly_detector.py")).read())
print("AnomalyDetector: OK (syntax valid)")

print("\n=== Testing HabitPredictor ===")
exec(open(os.path.join(ml_dir, "patterns", "habit_predictor.py")).read())
print("HabitPredictor: OK (syntax valid)")

print("\n=== Testing EnergyOptimizer ===")
exec(open(os.path.join(ml_dir, "patterns", "energy_optimizer.py")).read())
print("EnergyOptimizer: OK (syntax valid)")

print("\n=== Testing MultiUserLearner ===")
exec(open(os.path.join(ml_dir, "patterns", "multi_user_learner.py")).read())
print("MultiUserLearner: OK (syntax valid)")

print("\n=== Testing Training Pipeline ===")
exec(open(os.path.join(ml_dir, "training", "__init__.py")).read())
print("Training Pipeline: OK (syntax valid)")

print("\n=== Testing Inference Engine ===")
exec(open(os.path.join(ml_dir, "inference", "__init__.py")).read())
print("Inference Engine: OK (syntax valid)")

print("\n=== Testing ML Context ===")
# Just check file exists and has valid Python syntax
ml_context_path = os.path.join(os.path.dirname(ml_dir), "ml_context.py")
with open(ml_context_path, 'r') as f:
    code = f.read()
    compile(code, ml_context_path, 'exec')
print("ML Context: OK (syntax valid)")

print("\n=== All ML modules syntax validated successfully! ===")
