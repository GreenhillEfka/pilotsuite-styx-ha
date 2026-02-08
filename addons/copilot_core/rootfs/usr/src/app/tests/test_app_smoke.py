import os
import tempfile
import unittest

try:
    from copilot_core.app import create_app
except ModuleNotFoundError:
    # Allows running in minimal environments without Flask installed.
    create_app = None


class TestAppSmoke(unittest.TestCase):
    def test_create_app_and_health(self):
        if create_app is None:
            self.skipTest("Flask not installed")
        app = create_app()
        client = app.test_client()
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get("ok"))

    def test_capabilities_includes_brain_graph(self):
        if create_app is None:
            self.skipTest("Flask not installed")
        app = create_app()
        client = app.test_client()
        r = client.get("/api/v1/capabilities")
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get("ok"))
        self.assertIn("brain_graph", j.get("modules", {}))


if __name__ == "__main__":
    unittest.main()
