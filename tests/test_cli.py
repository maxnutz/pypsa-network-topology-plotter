"""
Tests for the CLI in energy_balance_evaluation.pypsa_network_eval.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

import pypsa
import pytest


def _make_two_carrier_network() -> pypsa.Network:
    """A minimal network with 'gas' and 'coal' carriers."""
    n = pypsa.Network()
    n.add("Carrier", "gas")
    n.add("Carrier", "coal")

    n.add("Bus", "bus_gas", carrier="gas")
    n.add("Bus", "bus_coal", carrier="coal")

    n.add("Generator", "gen_gas", bus="bus_gas", carrier="gas", p_nom=100)
    n.add("Generator", "gen_coal", bus="bus_coal", carrier="coal", p_nom=50)

    n.add("Load", "load_gas", bus="bus_gas", carrier="gas", p_set=40)
    n.add("Load", "load_coal", bus="bus_coal", carrier="coal", p_set=20)
    return n


class TestParseCarriers(unittest.TestCase):
    """Unit tests for the _parse_carriers helper."""

    def _fn(self, *args: str):
        from energy_balance_evaluation.pypsa_network_eval import _parse_carriers

        return _parse_carriers(list(args))

    def test_single_carrier_returns_list_of_one(self):
        result = self._fn("gas")
        self.assertEqual(result, ["gas"])

    def test_json_list_two_carriers(self):
        result = self._fn('["gas", "coal"]')
        self.assertEqual(result, ["gas", "coal"])

    def test_json_list_single_carrier(self):
        result = self._fn('["gas"]')
        self.assertEqual(result, ["gas"])

    def test_carrier_with_space_single(self):
        result = self._fn("agriculture electricity")
        self.assertEqual(result, ["agriculture electricity"])

    def test_json_list_with_spaced_carriers(self):
        result = self._fn('["agriculture electricity", "agriculture heat"]')
        self.assertEqual(result, ["agriculture electricity", "agriculture heat"])

    def test_invalid_json_treated_as_single_carrier(self):
        # A string starting with '[' but not valid JSON falls back to single carrier
        result = self._fn("[not valid json")
        self.assertEqual(result, ["[not valid json"])

    def test_bare_list_without_outer_quotes(self):
        # ["gas", "coal"] – no surrounding single-quotes (shell passes it as-is)
        result = self._fn('["gas", "coal"]')
        self.assertEqual(result, ["gas", "coal"])

    def test_comma_separated_quoted_strings(self):
        # '"gas", "coal"' – quoted strings without list brackets
        result = self._fn('"gas", "coal"')
        self.assertEqual(result, ["gas", "coal"])

    def test_comma_separated_quoted_strings_with_spaces(self):
        result = self._fn('"agriculture electricity", "agriculture heat"')
        self.assertEqual(result, ["agriculture electricity", "agriculture heat"])

    def test_multiple_plain_positional_args(self):
        # gas coal electricity – each passed as a separate shell argument
        result = self._fn("gas", "coal", "electricity")
        self.assertEqual(result, ["gas", "coal", "electricity"])


def _run_main(argv: list[str]) -> None:
    from energy_balance_evaluation.pypsa_network_eval import main

    with patch("sys.argv", ["pypsa-topology", *argv]):
        main()


@pytest.fixture
def nc_file(tmp_path: Path) -> Path:
    path = tmp_path / "test_network.nc"
    _make_two_carrier_network().export_to_netcdf(str(path))
    return path


def test_multiple_carriers_each_get_html(nc_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run_main([str(nc_file), '["gas", "coal"]', "--output-dir", str(out)])
    assert (out / "gas.html").exists()
    assert (out / "coal.html").exists()


def test_region_in_filename(nc_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    _run_main([str(nc_file), "gas", "--region", "bus_gas", "--output-dir", str(out)])
    assert (out / "gas_bus_gas.html").exists()


def test_unknown_carrier_exits_nonzero(nc_file: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as exc:
        _run_main([str(nc_file), "gas", "nonexistent", "--output-dir", str(out)])
    assert exc.value.code == 1
    assert (out / "gas.html").exists(), "valid carriers are still processed"


if __name__ == "__main__":
    unittest.main()
