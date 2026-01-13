import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend to Python path to import modules
sys.path.insert(0, str(Path(__file__).parent / ".."))

from analyze_entities import get_all_entities, get_entity_info


class TestAnalyzeEntities(unittest.TestCase):
    """Test cases for analyze_entities.py functions"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_entity_id = "light.test_light"
        self.valid_headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
        }

    @patch("analyze_entities.requests.get")
    def test_get_entity_info_success(self, mock_get):
        """Test getting entity info successfully."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity_id": self.test_entity_id,
            "state": "on",
            "attributes": {"brightness": 255},
        }
        mock_get.return_value = mock_response

        result = get_entity_info(self.test_entity_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["entity_id"], self.test_entity_id)
        self.assertEqual(result["state"], "on")
        mock_get.assert_called_once()

    @patch("analyze_entities.requests.get")
    def test_get_entity_info_failure(self, mock_get):
        """Test getting entity info with failure."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = get_entity_info(self.test_entity_id)

        self.assertIsNone(result)

    @patch("analyze_entities.requests.get")
    def test_get_entity_info_exception(self, mock_get):
        """Test getting entity info with exception."""
        # Mock exception
        mock_get.side_effect = Exception("Connection error")

        result = get_entity_info(self.test_entity_id)

        self.assertIsNone(result)

    @patch("analyze_entities.requests.get")
    def test_get_all_entities_success(self, mock_get):
        """Test getting all entities successfully."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"entity_id": "light.bedroom", "state": "off"},
            {"entity_id": "switch.outlet", "state": "on"},
        ]
        mock_get.return_value = mock_response

        result = get_all_entities()

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["entity_id"], "light.bedroom")

    @patch("analyze_entities.requests.get")
    def test_get_all_entities_failure(self, mock_get):
        """Test getting all entities with failure."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_all_entities()

        self.assertIsNone(result)


def run_analyze_entities_tests():
    """Run the tests for analyze_entities.py functions."""
    print("Testing analyze_entities.py Functions")
    print("=" * 50)
    print("This test verifies the functionality of analyze_entities.py.")

    # Create a test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAnalyzeEntities)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\nTest Results:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    if result.failures:
        print("  Failures:", [test[0]._testMethodName for test in result.failures])
    if result.errors:
        print("  Errors:", [test[0]._testMethodName for test in result.errors])

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_analyze_entities_tests()
    print("\n" + "=" * 50)
    if success:
        print("Analyze entities tests passed!")
    else:
        print("Some analyze entities tests failed.")
        sys.exit(1)
