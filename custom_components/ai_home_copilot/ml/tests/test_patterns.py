"""Tests for ML Pattern Recognition Module."""

import unittest
import time
import sys
import os

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



class TestAnomalyDetector(unittest.TestCase):
    """Test AnomalyDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..patterns.anomaly_detector import AnomalyDetector
        
        self.detector = AnomalyDetector(
            window_size=50,
            contamination=0.1,
            enabled=True,
        )
        self.detector.initialize_features(["feature1", "feature2"])
        
    def test_initialization(self):
        """Test detector initialization."""
        self.assertTrue(self.detector.enabled)
        self.assertEqual(len(self.detector.feature_names), 2)
        
    def test_update_and_detection(self):
        """Test feature update and anomaly detection."""
        features = {"feature1": 1.0, "feature2": 2.0}
        score, is_anomaly = self.detector.update(features)
        
        # Before training, should use fallback mode
        self.assertIsInstance(score, float)
        self.assertIsInstance(is_anomaly, bool)
        
    def test_anomaly_summary(self):
        """Test anomaly summary generation."""
        # Update with some data
        for i in range(10):
            self.detector.update({"feature1": float(i), "feature2": float(i * 2)})
            
        summary = self.detector.get_anomaly_summary(hours=24)
        
        self.assertIn("count", summary)
        self.assertIn("last_anomaly", summary)


class TestHabitPredictor(unittest.TestCase):
    """Test HabitPredictor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..patterns.habit_predictor import HabitPredictor
        
        self.predictor = HabitPredictor(
            min_samples_per_pattern=2,
            confidence_threshold=0.5,
            enabled=True,
        )
        
    def test_initialization(self):
        """Test predictor initialization."""
        self.assertTrue(self.predictor.enabled)
        
    def test_observe_and_predict(self):
        """Test observing events and making predictions."""
        device_id = "light.living_room"
        event_type = "on"
        
        # Observe multiple events at similar times
        for hour in [8, 9, 10]:
            timestamp = time.time() - (24 - hour) * 3600
            self.predictor.observe(
                device_id,
                event_type,
                timestamp,
                {"device_chain": ["light.living_room", "switch.main"]},
            )
            
        # Make prediction
        prediction = self.predictor.predict(device_id, event_type)
        
        self.assertIn("predicted", prediction)
        self.assertIn("confidence", prediction)
        
    def test_sequence_prediction(self):
        """Test sequence pattern prediction."""
        # Add sequence data
        self.predictor.observe(
            "light.living_room",
            "on",
            context={"device_chain": ["light.living_room", "switch.main"]},
        )
        
        prediction = self.predictor.predict_sequence("light.living_room")
        
        self.assertIn("predicted", prediction)
        self.assertIn("sequence", prediction)


class TestEnergyOptimizer(unittest.TestCase):
    """Test EnergyOptimizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..patterns.energy_optimizer import EnergyOptimizer
        
        self.optimizer = EnergyOptimizer(
            baseline_window_hours=168,
            enabled=True,
        )
        
    def test_initialization(self):
        """Test optimizer initialization."""
        self.assertTrue(self.optimizer.enabled)
        
    def test_register_and_record(self):
        """Test device registration and consumption recording."""
        device_id = "light.living_room"
        self.optimizer.register_device(device_id, 10.0, "light")
        
        # Record consumption
        self.optimizer.record_consumption(
            device_id,
            power_watts=8.0,
            duration_seconds=3600,
            context={"cost": 0.02},
        )
        
        # Get baseline
        baseline = self.optimizer.calculate_baseline(device_id)
        
        self.assertIn("mean_wh", baseline)
        
    def test_recommendations(self):
        """Test recommendation generation."""
        device_id = "light.living_room"
        self.optimizer.register_device(device_id, 10.0, "light")
        
        # Record baseline consumption
        for i in range(10):
            self.optimizer.record_consumption(
                device_id,
                power_watts=8.0,
                duration_seconds=3600,
            )
            
        # Get recommendations (should be empty - normal consumption)
        recommendations = self.optimizer.generate_recommendations(device_id, 8.0)
        
        self.assertIsInstance(recommendations, list)


class TestMultiUserLearner(unittest.TestCase):
    """Test MultiUserLearner class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..patterns.multi_user_learner import MultiUserLearner
        
        self.learner = MultiUserLearner(
            min_samples_per_user=2,
            similarity_threshold=0.5,
            enabled=True,
        )
        
    def test_initialization(self):
        """Test learner initialization."""
        self.assertTrue(self.learner.enabled)
        
    def test_user_event_recording(self):
        """Test recording user events."""
        user_id = "user1"
        self.learner.record_user_event(
            user_id,
            "arrive",
            {"location": "home", "timestamp": time.time()},
        )
        
        status = self.learner.get_user_status(user_id)
        
        self.assertIn("present", status)
        
    def test_preference_learning(self):
        """Test preference learning from setting changes."""
        user_id = "user1"
        
        # Record setting changes
        for value in [20, 21, 22]:
            self.learner.record_user_event(
                user_id,
                "setting_change",
                {
                    "device": "climate.living_room",
                    "value": value,
                    "timestamp": time.time(),
                },
            )
            
        # Get preference
        preference = self.learner.get_user_preference(user_id, "climate.living_room")
        
        self.assertIsNotNone(preference)
        
    def test_similar_users(self):
        """Test finding similar users."""
        # Add similar users
        for user_id in ["user1", "user2"]:
            for value in [20, 21, 22]:
                self.learner.record_user_event(
                    user_id,
                    "setting_change",
                    {
                        "device": "climate.living_room",
                        "value": value,
                        "timestamp": time.time(),
                    },
                )
                
        similar = self.learner.find_similar_users("user1")
        
        self.assertIsInstance(similar, list)


if __name__ == "__main__":
    unittest.main()
