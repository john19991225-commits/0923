import unittest

import pandas as pd

from live_weather import parse_stations
from weather_map import build_live_weather_map, observation_color, weather_icon


class LiveWeatherTests(unittest.TestCase):
    def setUp(self):
        self.stations = pd.DataFrame([{
            "stationName": "測試站", "stationId": "TEST", "county": "臺北市", "town": "中正區",
            "latitude": 25.04, "longitude": 121.52, "obsTime": "2026-09-23T16:00:00+08:00",
            "weather": "多雲", "temperature": 28.0, "humidity": 75.0,
            "precipitation": 3.0, "windSpeed": 4.0, "windDirection": 90.0,
            "pressure": 1008.0, "uvIndex": 2.0,
        }])

    def test_parse_cwa_station(self):
        payload = {"records": {"Station": [{
            "StationName": "測試站", "StationId": "TEST", "ObsTime": {"DateTime": "now"},
            "GeoInfo": {"CountyName": "臺北市", "TownName": "中正區", "Coordinates": [{
                "CoordinateName": "WGS84", "StationLatitude": "25.04", "StationLongitude": "121.52"
            }]},
            "WeatherElement": {"Weather": "多雲", "Now": {"Precipitation": "3"},
                               "AirTemperature": "28", "RelativeHumidity": "75",
                               "WindSpeed": "4", "WindDirection": "90"}
        }]}}
        result = parse_stations(payload)
        self.assertEqual(result.iloc[0]["stationName"], "測試站")
        self.assertEqual(result.iloc[0]["temperature"], 28.0)

    def test_layer_colors_and_icon(self):
        self.assertEqual(observation_color("temperature", 33), "#d73027")
        self.assertEqual(observation_color("precipitation", 5), "#22c55e")
        self.assertEqual(weather_icon("多雲"), "⛅")

    def test_all_map_modes_render(self):
        radar = {"host": "https://example.com", "frame": {"path": "/radar", "time": 1}}
        typhoons = [{"name": "測試颱風", "analysis": [{"CoordinateLatitude": "20", "CoordinateLongitude": "130"}],
                     "forecast": [{"CoordinateLatitude": "21", "CoordinateLongitude": "129"}]}]
        for mode in ("temperature", "precipitation", "radar", "typhoon", "wind", "humidity", "weather", "stations"):
            rendered = build_live_weather_map(self.stations, mode=mode, radar=radar, typhoons=typhoons).get_root().render()
            self.assertIn("測試站", rendered)


if __name__ == "__main__":
    unittest.main()
