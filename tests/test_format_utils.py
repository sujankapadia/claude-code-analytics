"""Tests for format_utils module."""

from claude_code_analytics.streamlit_app.services.format_utils import (
    format_char_count,
    format_duration,
    format_percentage,
)


class TestFormatDuration:
    """Tests for format_duration."""

    def test_zero_seconds(self):
        assert format_duration(0) == "0s"

    def test_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2m 5s"

    def test_hours_minutes_seconds(self):
        assert format_duration(3725) == "1h 2m 5s"

    def test_exact_minutes(self):
        assert format_duration(120) == "2m"

    def test_exact_hours(self):
        assert format_duration(3600) == "1h"

    def test_hours_and_seconds_no_minutes(self):
        assert format_duration(3601) == "1h 1s"

    def test_float_input(self):
        assert format_duration(90.7) == "1m 30s"

    def test_negative_input(self):
        assert format_duration(-5) == "0s"

    def test_large_value(self):
        assert format_duration(86400) == "24h"


class TestFormatCharCount:
    """Tests for format_char_count."""

    def test_small_value(self):
        assert format_char_count(500) == "500"

    def test_boundary_999(self):
        assert format_char_count(999) == "999"

    def test_one_thousand(self):
        assert format_char_count(1000) == "1.0K"

    def test_thousands(self):
        assert format_char_count(1500) == "1.5K"

    def test_large_thousands(self):
        assert format_char_count(999_999) == "1000.0K"

    def test_one_million(self):
        assert format_char_count(1_000_000) == "1.0M"

    def test_millions(self):
        assert format_char_count(2_500_000) == "2.5M"

    def test_zero(self):
        assert format_char_count(0) == "0"


class TestFormatPercentage:
    """Tests for format_percentage."""

    def test_typical_ratio(self):
        assert format_percentage(4200, 39300) == "10.7%"

    def test_zero_total(self):
        assert format_percentage(0, 0) == "0.0%"

    def test_full_percentage(self):
        assert format_percentage(100, 100) == "100.0%"

    def test_zero_part(self):
        assert format_percentage(0, 100) == "0.0%"

    def test_small_percentage(self):
        assert format_percentage(1, 1000) == "0.1%"
