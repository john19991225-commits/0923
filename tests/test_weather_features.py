import unittest

import pandas as pd

from weather_data import available_dates, weather_for_date
from weather_extensions import build_agriculture_alerts, fallback_advice
from weather_map import build_temperature_map, temperature_color


class WeatherFeatureTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            {"regionName": "臺北市", "dataDate": pd.Timestamp("2026-09-23"), "mint": 18.0, "maxt": 29.0},
            {"regionName": "高雄市", "dataDate": pd.Timestamp("2026-09-24"), "mint": 26.0, "maxt": 36.0},
        ])

    def test_temperature_colors(self):
        self.assertEqual(temperature_color(19), "#2c7bb6")
        self.assertEqual(temperature_color(22), "#7fcdbb")
        self.assertEqual(temperature_color(28), "#fdae61")
        self.assertEqual(temperature_color(31), "#d73027")

    def test_date_filter(self):
        dates = available_dates(self.data)
        self.assertEqual(len(dates), 2)
        filtered = weather_for_date(self.data, dates[0])
        self.assertEqual(filtered.iloc[0]["regionName"], "臺北市")

    def test_alerts(self):
        alerts = build_agriculture_alerts(self.data.to_dict("records"))
        self.assertEqual(len(alerts), 2)
        self.assertIn("日溫差", alerts[0]["message"])
        self.assertIn("高溫", alerts[1]["message"])

    def test_fallback_advice(self):
        self.assertIn("臺北市", fallback_advice("臺北市", 18, 29))

    def test_map_contains_markers(self):
        rendered = build_temperature_map(self.data).get_root().render()
        self.assertIn("臺北市", rendered)
        self.assertIn("高雄市", rendered)
        self.assertIn("display_name", rendered)


if __name__ == "__main__":
    unittest.main()
