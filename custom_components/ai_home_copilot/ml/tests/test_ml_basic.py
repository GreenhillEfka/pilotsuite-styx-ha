"""Basic tests for ML Pattern Recognition Module - standalone mode."""

import unittest
import time
import sys
import os

# Standalone test - import only what we need
test_dir = os.path.dirname(os.path.abspath(__file__))

# Add ML directory directly
ml_dir = os.path.dirname(test_dir)
sys.path.insert(0, ml_dir)


class TestAnomalyDetectorBasic(unittest.TestCase):
    """Test AnomalyDetector class - basic."""
    
    def test_detector_creation(self):
        """Test detector creation."""
        # Import directly without HA dependencies
        from patterns.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector(
            window_size=50,
            contamination=0.1,
            enabled=True,
        )
        
        self.assertTrue(detector.enabled)
        
    def test_detector_features(self):
        """Test feature initialization."""
        from patterns.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector(enabled=True)
        detector.initialize_features(["feature1", "feature2", "feature3"])
        
        self.assertEqual(len(detector.feature_names), 3)
        
    def test_pattern_update(self):
        """Test pattern update without HA."""
        from patterns.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector(enabled=True)
        detector.initialize_features(["power", "duration"])
        
        # Update with sample data
        features = {"power": 10.0, "duration": 3600}
        score, is_anomaly = detector.update(features)
        
        self.assertIsInstance(score, float)
        self.assertIsInstance(is_anomaly, bool)


class TestHabitPredictorBasic(unittest.TestCase):
    """Test HabitPredictor class - basic."""
    
    def test_predictor_creation(self):
        """Test predictor creation."""
        from patterns.habit_predictor import HabitPredictor
        
        predictor = HabitPredictor(
            min_samples_per_pattern=2,
            confidence_threshold=0.5,
            enabled=True,
        )
        
        self.assertTrue(predictor.enabled)
        
    def test_observe_event(self):
        """Test observing events."""
        from patterns.habit_predictor import HabitPredictor
        
        predictor = HabitPredictor(enabled=True)
        
        # Observe some events
        predictor.observe("light.kitchen", "on", time.time() - 3600)
        predictor.observe("light.kitchen", "on", time.time() - 7200)
        
        self.assertTrue(predictor._is_initialized)
        
    def test_sequence_prediction(self):
        """Test sequence prediction."""
        from patterns.habit_predictor import HabitPredictor
        
        predictor = HabitPredictor(enabled=True)
        
        # Add sequence
        predictor.observe(
            "light.kitchen",
            "on",
            context={"device_chain": ["light.kitchen", "switch.main"]}
        )
        
        prediction = predictor.predict_sequence("light.kitchen")
        
        self.assertIn("predicted", prediction)


class TestEnergyOptimizerBasic(unittest.TestCase):
    """Test EnergyOptimizer class - basic."""
    
    def test_optimizer_creation(self):
        """Test optimizer creation."""
        from patterns.energy_optimizer import EnergyOptimizer
        
        optimizer = EnergyOptimizer(
            baseline_window_hours=168,
            enabled=True,
        )
        
        self.assertTrue(optimizer.enabled)
        
    def test_register_device(self):
        """Test device registration."""
        from patterns.energy_optimizer import EnergyOptimizer
        
        optimizer = EnergyOptimizer(enabled=True)
        optimizer.register_device("light.kitchen", 10.0, "light")
        
        self.assertIn("light.kitchen", optimizer.device_profiles)
        
    def test_record_consumption(self):
        """Test consumption recording."""
        from patterns.energy_optimizer import EnergyOptimizer
        
        optimizer = EnergyOptimizer(enabled=True)
        optimizer.register_device("light.kitchen", 10.0, "light")
        
        optimizer.record_consumption(
            "light.kitchen",
            power_watts=8.0,
            duration_seconds=3600,
        )
        
        baseline = optimizer.calculate_baseline("light.kitchen")
        self.assertIn("mean_wh", baseline)


class TestMultiUserLearnerBasic(unittest.TestCase):
    """Test MultiUserLearner class - basic."""
    
    def test_learner_creation(self):
        """Test learner creation."""
        from patterns.multi_user_learner import MultiUserLearner
        
        learner = MultiUserLearner(
            min_samples_per_user=2,
            similarity_threshold=0.5,
            enabled=True,
        )
        
        self.assertTrue(learner.enabled)
        
    def test_record_user_event(self):
        """Test recording user events."""
        from patterns.multi_user_learner import MultiUserLearner
        
        learner = MultiUserLearner(enabled=True)
        
        learner.record_user_event(
            "user1",
            "arrive",
            {"location": "home", "timestamp": time.time()},
        )
        
        status = learner.get_user_status("user1")
        self.assertIn("present", status)
        
    def test_preference_learning(self):
        """Test preference learning."""
        from patterns.multi_user_learner import MultiUserLearner
        
        learner = MultiUserLearner(enabled=True)
        
        for value in [20, 21, 22]:
            learner.record_user_event(
                "user1",
                "setting_change",
                {
                    "device": "climate.living_room",
                    "value": value,
                    "timestamp": time.time(),
                },
            )
            
        preference = learner.get_user_preference("user1", "climate.living_room")
        self.assertIsNotNone(preference)


if __name__ == "__main__":
    unittest.main(verbosity=2)
