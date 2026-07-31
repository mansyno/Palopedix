"""Tests for the Click CLI wrapper."""

from click.testing import CliRunner
import pytest
from unittest.mock import patch

from palengine.cli.main import cli


@pytest.fixture
def mock_pals_data():
    return [
        {
            "internal_name": "Anubis",
            "display_name": "Anubis",
            "paldex_number": 100,
            "element_1": "Ground",
            "element_2": None,
            "breeding_power": 570,
            "nocturnal": 0,
            "size": "M",
            "is_variant": 0,
        }
    ]


def test_cli_pals_command(mock_pals_data):
    runner = CliRunner()
    with patch("palengine.db.sqlite_engine.SQLiteEngine.query_pals", return_value=mock_pals_data):
        result = runner.invoke(cli, ["pals", "--element", "Ground"])
        assert result.exit_code == 0
        assert "Anubis" in result.output
        assert "Ground" in result.output


def test_cli_breed_command():
    runner = CliRunner()
    mock_child = {
        "display_name": "Relaxaurus Lux",
        "paldex_number": 80,
        "breeding_power": 200,
        "element_1": "Electric",
        "element_2": "Dragon",
    }
    with patch("palengine.db.sqlite_engine.SQLiteEngine.get_breeding_result", return_value=mock_child):
        result = runner.invoke(cli, ["breed", "Relaxaurus", "Sparkit"])
        assert result.exit_code == 0
        assert "Relaxaurus Lux" in result.output
        assert "Electric" in result.output
