"""Tests for soil moisture integration module."""
import unittest
from unittest.mock import patch, MagicMock
from src.soil_moisture import (
    SoilMoistureClient,
    format_moisture_report,
    get_moisture_status,
    get_moisture_for_olive_analysis,
)


class TestSoilMoistureClient(unittest.TestCase):
    """Tests for SoilMoistureClient."""

    def test_init_with_config(self):
        """Client can be initialized with config dict."""
        config = {
            "api_base_url": "https://example.com",
            "api_key": "test-key",
            "default_kit_id": "test-kit",
            "timeout": 5,
            "cache_ttl": 30,
        }
        client = SoilMoistureClient(config)
        self.assertEqual(client.base_url, "https://example.com")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.default_kit_id, "test-kit")
        self.assertEqual(client.timeout, 5)
        self.assertEqual(client.cache_ttl, 30)

    def test_init_default_config(self):
        """Client can be initialized with minimal config."""
        client = SoilMoistureClient({})
        self.assertEqual(client.base_url, "")
        self.assertEqual(client.api_key, "")
        self.assertEqual(client.default_kit_id, "default")

    def test_cache(self):
        """Cache works correctly."""
        client = SoilMoistureClient({"cache_ttl": 60})
        client._cache["test"] = (1000.0, {"data": "cached"})
        # Cache hit
        self.assertIn("test", client._cache)
        # Clear cache
        client.clear_cache()
        self.assertEqual(len(client._cache), 0)

    def test_no_base_url_raises(self):
        """Request without base URL raises ValueError."""
        client = SoilMoistureClient({})
        with self.assertRaises(ValueError):
            client._get("/api/test")


class TestFormatMoistureReport(unittest.TestCase):
    """Tests for format_moisture_report."""

    def test_none_data(self):
        """None data returns unavailable message."""
        result = format_moisture_report(None)
        self.assertIn("No soil moisture data", result)

    def test_basic_report(self):
        """Basic report includes moisture values."""
        data = {
            "measured_at": "2026-08-21 10:00:00",
            "sensor1_moisture_percent": 45.5,
            "sensor2_moisture_percent": 52.3,
            "temperature": 25.0,
            "humidity": 60.0,
            "pressure": 1013.0,
        }
        result = format_moisture_report(data)
        self.assertIn("Sensor 1: 45.5%", result)
        self.assertIn("Sensor 2: 52.3%", result)
        self.assertIn("Average:", result)
        self.assertIn("48.9%", result)
        self.assertIn("Temperature:", result)
        self.assertIn("25.0", result)
        self.assertIn("Humidity:", result)
        self.assertIn("60.0", result)
        self.assertIn("Pressure:", result)
        self.assertIn("1013.0", result)

    def test_report_with_stats(self):
        """Report includes stats when provided."""
        data = {
            "sensor1_moisture_percent": 45.0,
            "sensor2_moisture_percent": 55.0,
        }
        stats = {
            "total_readings": 100,
            "sensor1_avg": 42.0,
            "sensor1_min": 30.0,
            "sensor1_max": 60.0,
            "sensor2_avg": 50.0,
            "sensor2_min": 35.0,
            "sensor2_max": 65.0,
        }
        result = format_moisture_report(data, stats)
        self.assertIn("100 readings", result)
        self.assertIn("Sensor 1 avg: 42.0%", result)


class TestGetMoistureStatus(unittest.TestCase):
    """Tests for get_moisture_status."""

    def test_unknown(self):
        """None data returns unknown."""
        self.assertEqual(get_moisture_status(None), "unknown")

    def test_dry(self):
        """Low moisture returns dry."""
        data = {"sensor1_moisture_percent": 15.0}
        self.assertEqual(get_moisture_status(data), "dry")

    def test_optimal(self):
        """Medium moisture returns optimal."""
        data = {"sensor1_moisture_percent": 50.0}
        self.assertEqual(get_moisture_status(data), "optimal")

    def test_wet(self):
        """High moisture returns wet."""
        data = {"sensor1_moisture_percent": 80.0}
        self.assertEqual(get_moisture_status(data), "wet")

    def test_average_of_two_sensors(self):
        """Status uses average of two sensors."""
        data = {
            "sensor1_moisture_percent": 20.0,
            "sensor2_moisture_percent": 40.0,
        }
        # Average = 30.0, which is optimal (30 <= avg < 70)
        self.assertEqual(get_moisture_status(data), "optimal")


class TestGetMoistureForOliveAnalysis(unittest.TestCase):
    """Tests for get_moisture_for_olive_analysis."""

    def test_returns_structure(self):
        """Returns expected structure."""
        result = get_moisture_for_olive_analysis(SoilMoistureClient({}))
        self.assertIn("soil_moisture", result)
        self.assertIn("available", result["soil_moisture"])
        self.assertIn("status", result["soil_moisture"])
        self.assertIn("source", result["soil_moisture"])

    def test_source_identifier(self):
        """Source is identified correctly."""
        result = get_moisture_for_olive_analysis(SoilMoistureClient({}))
        self.assertEqual(result["soil_moisture"]["source"], "ukk-kosen/soil-moisture")


if __name__ == "__main__":
    unittest.main()
