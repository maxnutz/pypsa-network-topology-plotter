"""
Tests for CLI additions in energy_balance_evaluation.pypsa_network_eval:
  - multiple carriers via JSON list
  - --plot-mermaid flag
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestProcessCarrier(unittest.TestCase):
    """Tests for _process_carrier – verifies .txt is always written."""

    def setUp(self):
        self.n = _make_two_carrier_network()

    def test_txt_file_written_plot_mermaid_true(self):
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import _process_carrier

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            # patch create_mermaid_output to avoid network call
            with patch(
                "energy_balance_evaluation.pypsa_network_eval.CarrierNetwork.create_mermaid_output"
            ):
                _process_carrier("gas", self.n, None, output_dir, plot_mermaid=True)
            txt = output_dir / "gas.txt"
            self.assertTrue(txt.exists(), "Mermaid .txt file should always be written")
            self.assertIn("flowchart", txt.read_text(encoding="utf-8"))

    def test_txt_file_written_plot_mermaid_false(self):
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import _process_carrier

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            _process_carrier("gas", self.n, None, output_dir, plot_mermaid=False)
            txt = output_dir / "gas.txt"
            self.assertTrue(txt.exists(), "Mermaid .txt file should always be written")

    def test_png_not_attempted_when_plot_mermaid_false(self):
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import _process_carrier

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            with patch(
                "energy_balance_evaluation.pypsa_network_eval.CarrierNetwork.create_mermaid_output"
            ) as mock_plot:
                _process_carrier("gas", self.n, None, output_dir, plot_mermaid=False)
            mock_plot.assert_not_called()

    def test_png_attempted_when_plot_mermaid_true(self):
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import _process_carrier

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            with patch(
                "energy_balance_evaluation.pypsa_network_eval.CarrierNetwork.create_mermaid_output"
            ) as mock_plot:
                _process_carrier("gas", self.n, None, output_dir, plot_mermaid=True)
            mock_plot.assert_called_once()


class TestMainMultipleCarriers(unittest.TestCase):
    """Integration-level tests for main() with multiple carriers."""

    def _make_nc_file(self, tmp_dir: Path) -> Path:
        n = _make_two_carrier_network()
        nc_path = tmp_dir / "test_network.nc"
        n.export_to_netcdf(str(nc_path))
        return nc_path

    def test_multiple_carriers_each_get_txt_file(self):
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nc_file = self._make_nc_file(tmp_path)
            resources_dir = tmp_path / "resources"

            original_path = Path

            def patched_path(arg="", *a, **kw):
                if arg == "resources":
                    return resources_dir
                return original_path(arg, *a, **kw)

            with patch(
                "energy_balance_evaluation.pypsa_network_eval.Path",
                side_effect=patched_path,
            ):
                with patch(
                    "sys.argv",
                    ["pypsa-topology", str(nc_file), '["gas", "coal"]', "--plot-mermaid", "False"],
                ):
                    main()

            self.assertTrue((resources_dir / "gas.txt").exists())
            self.assertTrue((resources_dir / "coal.txt").exists())

    def test_plot_mermaid_false_skips_png(self):
        """When --plot-mermaid False, create_mermaid_output must not be called."""
        import tempfile

        from energy_balance_evaluation.pypsa_network_eval import main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nc_file = self._make_nc_file(tmp_path)
            resources_dir = tmp_path / "resources"

            original_path = Path

            def patched_path(arg="", *a, **kw):
                if arg == "resources":
                    return resources_dir
                return original_path(arg, *a, **kw)

            with patch(
                "energy_balance_evaluation.pypsa_network_eval.Path",
                side_effect=patched_path,
            ):
                with patch(
                    "energy_balance_evaluation.pypsa_network_eval.CarrierNetwork.create_mermaid_output"
                ) as mock_plot:
                    with patch(
                        "sys.argv",
                        ["pypsa-topology", str(nc_file), "gas", "--plot-mermaid", "False"],
                    ):
                        main()

            mock_plot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
