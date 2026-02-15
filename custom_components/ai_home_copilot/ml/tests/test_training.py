"""Tests for ML Training Module."""

import unittest
import sys
import os
from pathlib import Path

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



class TestTrainingPipeline(unittest.TestCase):
    """Test TrainingPipeline class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..training import TrainingPipeline
        
        storage_path = "/tmp/test_ml_training"
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        
        self.pipeline = TrainingPipeline(
            storage_path=storage_path,
            auto_save=False,
            enabled=True,
        )
        
    def test_initialization(self):
        """Test pipeline initialization."""
        self.assertTrue(self.pipeline.enabled)
        
    def test_add_training_data(self):
        """Test adding training data."""
        added = self.pipeline.add_training_data(
            "test_model",
            {"feature1": 1.0, "feature2": 2.0},
        )
        
        self.assertTrue(added)
        
    def test_train_model_not_registered(self):
        """Test training unregistered model."""
        result = self.pipeline.train_model("nonexistent")
        
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
