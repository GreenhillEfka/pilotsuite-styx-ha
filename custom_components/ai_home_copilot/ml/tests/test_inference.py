"""Tests for ML Inference Module."""

import unittest
import sys
import os
from pathlib import Path
import pickle
import json

# Add test directory and parent directories to path
test_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(test_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, test_dir)

# Mock homeassistant before importing other modules
class MockConfigEntry:
    pass

class MockHA:
    config_entries = type('obj', (object,), {'ConfigEntry': MockConfigEntry})()
    
sys.modules['homeassistant'] = MockHA()
sys.modules['homeassistant.config_entries'] = MockHA()



class TestInferenceEngine(unittest.TestCase):
    """Test InferenceEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..inference import InferenceEngine
        from sklearn.ensemble import IsolationForest
        
        storage_path = "/tmp/test_ml_inference"
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        
        # Create and save a test model
        model = IsolationForest(contamination=0.1)
        model.fit([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
        
        with open(Path(storage_path) / "test_anomaly_model.pkl", "wb") as f:
            pickle.dump(model, f)
            
        with open(Path(storage_path) / "test_anomaly_metadata.json", "w") as f:
            json.dump({"feature_names": ["feature1", "feature2"]}, f)
            
        self.engine = InferenceEngine(
            model_path=storage_path,
            cache_ttl_seconds=60,
            enabled=True,
        )
        
    def test_initialization(self):
        """Test engine initialization."""
        self.assertTrue(self.engine.enabled)
        
    def test_load_model(self):
        """Test model loading."""
        loaded = self.engine.load_model("test_anomaly")
        
        self.assertTrue(loaded)
        
    def test_predict(self):
        """Test prediction."""
        self.engine.load_model("test_anomaly")
        
        result = self.engine.predict(
            "test_anomaly",
            {"feature1": 1.5, "feature2": 3.0},
        )
        
        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
