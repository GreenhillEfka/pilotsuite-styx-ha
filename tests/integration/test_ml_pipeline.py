"""Integration test: ML Training → Inference - E2E."""

import pytest
import time
import sys
import os
import numpy as np
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add custom_components to path
custom_components = project_root / "custom_components"
if custom_components.exists():
    sys.path.insert(0, str(custom_components))


class TestMLPipelineIntegration:
    """Test complete ML pipeline from training to inference."""

    @pytest.mark.asyncio
    async def test_ml_training_to_inference(self, hass):
        """Test full ML pipeline: training data → model → inference."""
        # This test would verify:
        # 1. Training data collection works
        # 2. Model training succeeds
        # 3. Model is saved correctly
        # 4. Inference engine loads model
        # 5. Inference produces valid results
        
        # For now, test ML module structure
        ml_path = Path("custom_components/ai_home_copilot/ml")
        assert ml_path.exists()
        assert (ml_path / "patterns").exists()
        assert (ml_path / "training").exists()
        assert (ml_path / "inference").exists()
        
        assert True  # Structure verification

    @pytest.mark.asyncio
    async def test_anomaly_detection_pipeline(self, hass):
        """Test complete anomaly detection pipeline."""
        # Test:
        # 1. Feature collection
        # 2. Anomaly model training
        # 3. Real-time anomaly scoring
        # 4. Anomaly alert generation
        
        # Import from patterns module directly via custom_components path
        from ai_home_copilot import ml
        from ai_home_copilot.ml.patterns.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector(
            window_size=50,
            contamination=0.1,
            enabled=True,
        )
        detector.initialize_features(["power", "duration"])
        
        # Simulate training data
        for i in range(30):
            features = {"power": 10.0 + np.random.randn() * 0.5, "duration": 3600}
            detector.update(features)
        
        # Test inference
        test_features = {"power": 10.2, "duration": 3600}
        score, is_anomaly = detector.update(test_features)
        
        assert isinstance(score, float)
        assert isinstance(is_anomaly, bool)
        assert score >= 0 and score <= 1

    @pytest.mark.asyncio
    async def test_habit_prediction_pipeline(self, hass):
        """Test complete habit prediction pipeline."""
        # Test:
        # 1. Event observation
        # 2. Pattern learning
        # 3. Prediction generation
        
        from ai_home_copilot import ml
        from ai_home_copilot.ml.patterns.habit_predictor import HabitPredictor
        
        predictor = HabitPredictor(
            min_samples_per_pattern=2,
            confidence_threshold=0.5,
            enabled=True,
        )
        
        # Observe repeated pattern
        base_time = time.time()
        for hour in [8, 9, 10]:
            predictor.observe(
                "light.living_room",
                "on",
                base_time - (24 - hour) * 3600,
                {"device_chain": ["light.living_room", "switch.main"]},
            )
        
        # Test prediction
        prediction = predictor.predict("light.living_room", "on")
        
        assert "predicted" in prediction
        assert "confidence" in prediction
