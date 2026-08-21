"""
Soil Moisture Integration Module for OliveVision AI.

Fetches soil moisture data from the UKK-KOSEN Cloudflare D1 API
and provides it for integration with olive tree analysis.

This module does NOT modify any existing code - it is a standalone
addition that can be used independently or alongside OliveVision AI.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class SoilMoistureClient:
    """Client for the UKK-KOSEN soil moisture monitoring API."""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the soil moisture client.

        Args:
            config: Configuration dictionary. If None, loads from config/soil_moisture.yaml
        """
        if config is None:
            config = self._load_config()

        self.base_url = config.get("api_base_url", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.default_kit_id = config.get("default_kit_id", "default")
        self.timeout = config.get("timeout", 10)
        self.cache_ttl = config.get("cache_ttl", 60)

        self._cache: dict[str, tuple[float, Any]] = {}

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            import yaml
            config_path = "config/soil_moisture.yaml"
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make a GET request to the API."""
        if not self.base_url:
            raise ValueError("API base URL not configured")

        url = f"{self.base_url}{endpoint}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += f"?{query}"

        cache_key = url
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data

        headers = {}
        if self.api_key:
            headers["X-Sensor-Api-Key"] = self.api_key

        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                self._cache[cache_key] = (time.time(), data)
                return data
        except HTTPError as e:
            raise RuntimeError(f"API error {e.code}: {e.reason}") from e
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}") from e

    def get_latest(self, kit_id: Optional[str] = None) -> Optional[dict]:
        """
        Get the latest soil moisture reading.

        Args:
            kit_id: Kit identifier (uses default if not specified)

        Returns:
            Latest sensor data or None if unavailable
        """
        kit_id = kit_id or self.default_kit_id
        return self._get("/api/sensor/latest", {"kit_id": kit_id})

    def get_history(
        self,
        kit_id: Optional[str] = None,
        hours: int = 24,
        interval: str = "",
        limit: int = 100,
    ) -> list[dict]:
        """
        Get historical soil moisture data.

        Args:
            kit_id: Kit identifier
            hours: Number of hours to look back
            interval: Aggregation interval ('hourly', 'daily', or '' for raw)
            limit: Maximum number of records

        Returns:
            List of sensor data records
        """
        kit_id = kit_id or self.default_kit_id
        params = {
            "kit_id": kit_id,
            "hours": str(hours),
            "limit": str(limit),
        }
        if interval:
            params["interval"] = interval

        result = self._get("/api/sensor/history", params)
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return result if isinstance(result, list) else []

    def get_stats(
        self, kit_id: Optional[str] = None, hours: int = 24
    ) -> Optional[dict]:
        """
        Get soil moisture statistics.

        Args:
            kit_id: Kit identifier
            hours: Number of hours to calculate stats for

        Returns:
            Statistics dictionary or None
        """
        kit_id = kit_id or self.default_kit_id
        return self._get("/api/sensor/stats", {"kit_id": kit_id, "hours": str(hours)})

    def get_calibration(self, kit_id: Optional[str] = None) -> Optional[dict]:
        """
        Get calibration values for a kit.

        Args:
            kit_id: Kit identifier

        Returns:
            Calibration data or None
        """
        kit_id = kit_id or self.default_kit_id
        return self._get("/api/sensor/calibration", {"kit_id": kit_id})

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()


def format_moisture_report(data: Optional[dict], stats: Optional[dict] = None) -> str:
    """
    Format soil moisture data as a readable report.

    Args:
        data: Latest sensor data
        stats: Optional statistics data

    Returns:
        Formatted report string
    """
    if data is None:
        return "No soil moisture data available"

    lines = []
    lines.append("=== Soil Moisture Report ===")

    if data.get("measured_at") or data.get("timestamp"):
        ts = data.get("measured_at") or data.get("timestamp")
        lines.append(f"Time: {ts}")

    lines.append("")
    lines.append("--- Moisture Levels ---")
    s1 = data.get("sensor1_moisture_percent")
    s2 = data.get("sensor2_moisture_percent")
    if s1 is not None:
        lines.append(f"  Sensor 1: {s1:.1f}%")
    if s2 is not None:
        lines.append(f"  Sensor 2: {s2:.1f}%")
    if s1 is not None and s2 is not None:
        avg = (s1 + s2) / 2
        lines.append(f"  Average:  {avg:.1f}%")

    temp = data.get("temperature")
    hum = data.get("humidity")
    pres = data.get("pressure")
    if any(v is not None for v in [temp, hum, pres]):
        lines.append("")
        lines.append("--- Environment ---")
        if temp is not None:
            lines.append(f"  Temperature: {temp:.1f} C")
        if hum is not None:
            lines.append(f"  Humidity:    {hum:.1f}%")
        if pres is not None:
            lines.append(f"  Pressure:    {pres:.1f} hPa")

    if stats:
        lines.append("")
        lines.append(f"--- Statistics ({stats.get('total_readings', '?')} readings) ---")
        s1_avg = stats.get("sensor1_avg")
        s2_avg = stats.get("sensor2_avg")
        if s1_avg is not None:
            lines.append(f"  Sensor 1 avg: {s1_avg:.1f}% (min: {stats.get('sensor1_min', '?'):.1f}, max: {stats.get('sensor1_max', '?'):.1f})")
        if s2_avg is not None:
            lines.append(f"  Sensor 2 avg: {s2_avg:.1f}% (min: {stats.get('sensor2_min', '?'):.1f}, max: {stats.get('sensor2_max', '?'):.1f})")

    return "\n".join(lines)


def get_moisture_status(data: Optional[dict]) -> str:
    """
    Get a simple moisture status string.

    Args:
        data: Latest sensor data

    Returns:
        Status string: 'dry', 'optimal', 'wet', or 'unknown'
    """
    if data is None:
        return "unknown"

    s1 = data.get("sensor1_moisture_percent")
    s2 = data.get("sensor2_moisture_percent")

    if s1 is None and s2 is None:
        return "unknown"

    values = [v for v in [s1, s2] if v is not None]
    avg = sum(values) / len(values)

    if avg < 30:
        return "dry"
    elif avg < 70:
        return "optimal"
    else:
        return "wet"


def get_moisture_for_olive_analysis(
    client: Optional[SoilMoistureClient] = None,
    kit_id: Optional[str] = None,
) -> dict:
    """
    Get soil moisture data formatted for OliveVision AI integration.

    This function provides soil moisture data that can be added to
    olive tree analysis results without modifying the core analysis code.

    Args:
        client: SoilMoistureClient instance (creates new one if None)
        kit_id: Kit identifier

    Returns:
        Dictionary with soil moisture data suitable for integration
    """
    if client is None:
        client = SoilMoistureClient()

    try:
        latest = client.get_latest(kit_id)
        stats = client.get_stats(kit_id, hours=24)
        status = get_moisture_status(latest)

        result = {
            "soil_moisture": {
                "available": latest is not None,
                "status": status,
                "latest": latest,
                "stats_24h": stats,
                "source": "ukk-kosen/soil-moisture",
            }
        }

        if latest:
            s1 = latest.get("sensor1_moisture_percent")
            s2 = latest.get("sensor2_moisture_percent")
            values = [v for v in [s1, s2] if v is not None]
            if values:
                result["soil_moisture"]["average_percent"] = sum(values) / len(values)
                result["soil_moisture"]["sensor1_percent"] = s1
                result["soil_moisture"]["sensor2_percent"] = s2

            result["soil_moisture"]["temperature"] = latest.get("temperature")
            result["soil_moisture"]["humidity"] = latest.get("humidity")

        return result

    except Exception as e:
        return {
            "soil_moisture": {
                "available": False,
                "status": "error",
                "error": str(e),
                "source": "ukk-kosen/soil-moisture",
            }
        }
