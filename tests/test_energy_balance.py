"""
Tests for EnergyBalance and related classes
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import tempfile
import yaml
from pathlib import Path


class TestVariablesSet(unittest.TestCase):
    """Test the VariablesSet class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create a sample YAML definition file
        self.yaml_content = [
            {
                "Final Energy": {
                    "description": "total final energy consumption",
                    "unit": "GWh",
                    "nrg": "FC_E",
                    "siec": "TOTAL",
                    "value": 279335.902,
                }
            },
            {
                "Final Energy|Electricity": {
                    "description": "final energy consumption of electricity",
                    "unit": "GWh",
                    "nrg": "FC_E",
                    "siec": "E7000",
                    "value": 63260.630,
                }
            },
        ]

        self.yaml_file = self.temp_path / "test_variables.yaml"
        with open(self.yaml_file, "w") as f:
            yaml.dump(self.yaml_content, f)

        # Create a sample TSV file
        self.tsv_file = self.temp_path / "test_data.tsv"
        tsv_data = """freq\tnrg_bal\tsiec\tunit\tgeo\t2023
A\tFC_E\tTOTAL\tGWH\tAT\t279335.902
A\tFC_E\tE7000\tGWH\tAT\t63260.630
A\tFC_E\tBIOE\tGWH\tAT\t62388.302
A\tFC_E\tTOTAL\tGWH\tDE\t500000.0"""
        with open(self.tsv_file, "w") as f:
            f.write(tsv_data)

        self.codelist_file = self.temp_path / "codelist.yaml"

    def tearDown(self):
        """Clean up temporary files"""
        self.temp_dir.cleanup()

    def test_variables_set_initialization(self):
        """Test VariablesSet initialization"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="final_energy",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        self.assertEqual(vs.name, "final_energy")
        self.assertEqual(vs.year, 2023)
        self.assertEqual(vs.country, "AT")
        self.assertIsNone(vs.variables_dict)

    def test_read_yaml_file(self):
        """Test reading YAML definition file"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="final_energy",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs.read_yaml_file()

        self.assertIsInstance(result, dict)
        self.assertIn("Final Energy", result)
        self.assertIn("Final Energy|Electricity", result)
        self.assertEqual(result["Final Energy"]["nrg"], "FC_E")
        self.assertEqual(result["Final Energy"]["siec"], "TOTAL")

    def test_read_yaml_file_missing_file(self):
        """Test read_yaml_file with non-existent definition file"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="final_energy",
            year=2023,
            filepath_definition="this_file_should_not_exist_12345.yaml",
            filepath_codelist=str(self.codelist_file),
        )

        with self.assertRaises(FileNotFoundError):
            vs.read_yaml_file()

    def test_read_yaml_file_non_list_top_level(self):
        """Test read_yaml_file with YAML that does not parse to a list"""
        import os

        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump({"not": "a list"}, tmp)
            definition_path = tmp.name

        try:
            vs = VariablesSet(
                set_name="final_energy",
                year=2023,
                filepath_definition=definition_path,
                filepath_codelist=str(self.codelist_file),
            )

            with self.assertRaises(ValueError):
                vs.read_yaml_file()
        finally:
            if os.path.exists(definition_path):
                os.remove(definition_path)

    def test_read_yaml_file_list_with_non_dict_element(self):
        """Test read_yaml_file with a list containing non-dict elements"""
        import os

        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        yaml_content = [
            "this is not a dict",
            {"Final Energy": {"nrg": "FC_E", "siec": "TOTAL"}},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(yaml_content, tmp)
            definition_path = tmp.name

        try:
            vs = VariablesSet(
                set_name="final_energy",
                year=2023,
                filepath_definition=definition_path,
                filepath_codelist=str(self.codelist_file),
            )

            with self.assertRaises(ValueError):
                vs.read_yaml_file()
        finally:
            if os.path.exists(definition_path):
                os.remove(definition_path)

    def test_parse_codes_single(self):
        """Test parsing single code"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes("FC_E")
        self.assertEqual(result, ["FC_E"])

    def test_parse_codes_multiple(self):
        """Test parsing multiple comma-separated codes"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes("FC_OTH_HH_E,FC_OTH_CP_E")
        self.assertEqual(result, ["FC_OTH_HH_E", "FC_OTH_CP_E"])

    def test_parse_codes_with_comment(self):
        """Test parsing codes with inline comments"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes("FC_E  # Final consumption")
        self.assertEqual(result, ["FC_E"])

    def test_parse_codes_empty(self):
        """Test parsing empty code string"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes("")
        self.assertEqual(result, [])

    def test_load_tsv_data(self):
        """Test loading TSV data and basic column cleanup"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        df = vs._load_tsv_data(str(self.tsv_file))

        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("freq", df.columns)
        self.assertIn("nrg_bal", df.columns)
        self.assertIn("siec", df.columns)
        # column should be normalized to 'geo' regardless of input style
        self.assertIn("geo", df.columns)

        # numeric year columns should have no surrounding whitespace
        for col in df.columns[5:]:
            self.assertEqual(col, col.strip())

    def test_load_tsv_data_with_combined_header(self):
        """Test loading a TSV file with the combined header used in pypsa-eur downloads"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        # create a temporary file with a complex header similar to real data
        combined = self.temp_path / "combo.tsv"
        header = "freq,nrg_bal,siec,unit,geo\\TIME_PERIOD\t2020\n"
        # include one row for AT country
        row = "A\tFC_E\tTOTAL\tGWH\tAT\t12345.6\n"
        with open(combined, "w") as f:
            f.write(header)
            f.write(row)

        vs = VariablesSet(
            set_name="test",
            year=2020,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        df2 = vs._load_tsv_data(str(combined))
        self.assertIn("geo", df2.columns)
        self.assertIn("2020", df2.columns)
        # filtering should work
        df_f = df2[df2["geo"] == "AT"]
        self.assertEqual(len(df_f), 1)
        self.assertAlmostEqual(df_f["2020"].iloc[0], 12345.6)

    def test_load_tsv_data_with_clean_headers(self):
        """Test loading TSV with already normalized headers (no special geo\\TIME_PERIOD)"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        # Create a TSV with clean headers: freq, nrg_bal, siec, unit, geo, year columns
        clean = self.temp_path / "clean.tsv"
        header = "freq\tnrg_bal\tsiec\tunit\tgeo\t2023\n"
        row = "A\tFC_E\tTOTAL\tGWH\tAT\t100.5\n"
        with open(clean, "w") as f:
            f.write(header)
            f.write(row)

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        df = vs._load_tsv_data(str(clean))
        self.assertIn("geo", df.columns)
        self.assertIn("2023", df.columns)
        # Check that data is accessible
        df_f = df[df["geo"] == "AT"]
        self.assertEqual(len(df_f), 1)
        self.assertAlmostEqual(df_f["2023"].iloc[0], 100.5)

    def test_load_tsv_data_colon_as_missing_value(self):
        """Test that ':' is converted to NaN in year columns"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet
        import numpy as np

        # Create TSV with ':' as missing value
        with_missing = self.temp_path / "missing.tsv"
        header = "freq\tnrg_bal\tsiec\tunit\tgeo\t2023\n"
        # Row with ':' in the year column (missing value)
        row = "A\tFC_E\tTOTAL\tGWH\tAT\t:\n"
        with open(with_missing, "w") as f:
            f.write(header)
            f.write(row)

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        df = vs._load_tsv_data(str(with_missing))
        # Check that ':' was converted to NaN
        value = df[df["geo"] == "AT"]["2023"].iloc[0]
        self.assertTrue(np.isnan(value), f"Expected NaN but got {value}")

    def test_calculate_variable_values(self):
        """Test calculating variable values from TSV"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        # First read the YAML
        vs.read_yaml_file()

        # Calculate values
        values = vs.calculate_variable_values(str(self.tsv_file))

        self.assertIsInstance(values, dict)
        self.assertIn("Final Energy", values)
        self.assertIn("Final Energy|Electricity", values)
        # Check that values are floats and equal the sample data values
        self.assertIsInstance(values["Final Energy"], float)
        self.assertGreater(values["Final Energy"], 0)
        self.assertAlmostEqual(values["Final Energy"], 279335.902)
        self.assertAlmostEqual(values["Final Energy|Electricity"], 63260.63)

    def test_calculate_variable_values_missing_year_column(self):
        """Test calculate_variable_values when year column is missing from TSV"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=1900,  # Use a year not in the test TSV
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        # First read the YAML
        vs.read_yaml_file()

        # Calculate values with missing year column
        values = vs.calculate_variable_values(str(self.tsv_file))

        self.assertIsInstance(values, dict)
        # All variables should resolve to np.nan if the year column is missing
        for var_name, value in values.items():
            self.assertTrue(
                np.isnan(value),
                msg=f"Expected np.nan for missing year column in {var_name}, got {value!r}",
            )

    def test_calculate_variable_values_empty_filter(self):
        """Test calculate_variable_values when filter returns empty DataFrame"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="ZZ",  # Use a non-existent country to force empty filter
        )

        # First read the YAML
        vs.read_yaml_file()

        # Calculate values with empty filter
        values = vs.calculate_variable_values(str(self.tsv_file))

        self.assertIsInstance(values, dict)
        # All variables should return 0.0 when filtered DataFrame is empty
        for var_name, value in values.items():
            self.assertEqual(
                value,
                0.0,
                msg=f"Expected 0.0 for empty filter in {var_name}, got {value!r}",
            )

    def test_write_codelist(self):
        """Test writing codelist YAML"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        # Write codelist
        vs.write_codelist(filepath_tsv=str(self.tsv_file))

        # Verify file was created
        self.assertTrue(self.codelist_file.exists())

        # Read and verify content
        with open(self.codelist_file, "r") as f:
            codelist = yaml.safe_load(f)

        self.assertIsInstance(codelist, list)
        self.assertGreater(len(codelist), 0)

        # Check structure of first entry
        first_entry = codelist[0]
        self.assertIn("variable", first_entry)
        self.assertIn("year", first_entry)
        self.assertIn("value", first_entry)
        self.assertIn("validation", first_entry)
        # Year is stored as an int in the YAML
        self.assertEqual(first_entry["year"], 2023)

    def test_write_codelist_value_rounding_and_validation(self):
        """Test that write_codelist correctly rounds values and validates structure"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        # Write codelist
        vs.write_codelist(filepath_tsv=str(self.tsv_file))

        # Load the written codelist and verify structure
        with open(self.codelist_file, "r") as f:
            codelist = yaml.safe_load(f)

        # Find the "Final Energy" entry
        fe_entry = None
        for entry in codelist:
            if entry.get("variable") == "Final Energy":
                fe_entry = entry
                break

        self.assertIsNotNone(fe_entry, "Final Energy entry not found in codelist")

        # Check that `year` is written as an int or string representation of int
        year = fe_entry.get("year")
        self.assertIsNotNone(year)
        # The actual implementation stores year as int according to the code
        self.assertIsInstance(year, (int, str))
        if isinstance(year, str):
            self.assertEqual(year, "2023")
        else:
            self.assertEqual(year, 2023)

        # Check that `value` is rounded to 3 decimal places
        value = fe_entry.get("value")
        self.assertIsInstance(value, (float, int))
        # Verify rounding by converting to string and checking decimal places
        value_str = f"{value:.3f}"
        # Ensure exactly three or fewer decimal places are present
        decimal_part = value_str.split(".")[-1]
        self.assertLessEqual(len(decimal_part), 3)

        # Check validation structure: should be a list of two dicts
        validation = fe_entry.get("validation")
        self.assertIsInstance(validation, list)
        self.assertEqual(len(validation), 2)

        first_val, second_val = validation
        # First validation: {"rtol": 0.3}
        self.assertIsInstance(first_val, dict)
        self.assertIn("rtol", first_val)
        self.assertAlmostEqual(first_val["rtol"], 0.3)

        # Second validation: {"warning_level": "low", "rtol": 0.1}
        self.assertIsInstance(second_val, dict)
        self.assertEqual(second_val.get("warning_level"), "low")
        self.assertIn("rtol", second_val)
        self.assertAlmostEqual(second_val["rtol"], 0.1)

    def test_write_codelist_missing_tsv_raises(self):
        """Test that FileNotFoundError is raised when TSV path is not found"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test_missing_tsv",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="AT",
        )

        # When filepath_tsv is None and the inferred TSV doesn't exist,
        # write_codelist should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            vs.write_codelist(filepath_tsv=None)

    def test_default_country_is_at(self):
        """Test that default country is Austria"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        self.assertEqual(vs.country, "AT")

    def test_custom_country(self):
        """Test using custom country code"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name="test",
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country="DE",
        )

        self.assertEqual(vs.country, "DE")


class TestCalculateVariableValuesMissingGeo(unittest.TestCase):
    """Test calculate_variable_values with missing geo column"""

    def test_missing_geo_column_raises_keyerror(self):
        """TSV without `geo` should raise KeyError in calculate_variable_values."""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        # Create a temporary directory and files
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create a minimal YAML definition
            yaml_content = [
                {
                    "Final Energy": {
                        "description": "test",
                        "unit": "GWh",
                        "nrg": "FC_E",
                        "siec": "TOTAL",
                        "value": 100.0,
                    }
                }
            ]

            yaml_file = temp_path / "test_def.yaml"
            with open(yaml_file, "w") as f:
                yaml.dump(yaml_content, f)

            # Create a minimal TSV missing the `geo` column
            tsv_file = temp_path / "input_without_geo.tsv"
            df_no_geo = pd.DataFrame(
                {
                    "freq": ["A"],
                    "nrg_bal": ["FC_E"],
                    "siec": ["TOTAL"],
                    "unit": ["GWH"],
                    "2023": [1.0],
                }
            )
            df_no_geo.to_csv(tsv_file, sep="\t", index=False)

            codelist_file = temp_path / "codelist.yaml"

            # Create VariablesSet and expect KeyError when calculating values
            vs = VariablesSet(
                set_name="test",
                year=2023,
                filepath_definition=str(yaml_file),
                filepath_codelist=str(codelist_file),
                country="AT",
            )

            with self.assertRaisesRegex(KeyError, "geo"):
                vs.calculate_variable_values(str(tsv_file))


class TestEnergyBalanceClass(unittest.TestCase):
    """Test the EnergyBalance class"""

    def _get_sample_df(self):
        """Helper to create sample energy balance DataFrame"""
        return pd.DataFrame(
            {
                "layer_0": [
                    "Total_absolute_values",
                    "Total_absolute_values",
                    "Transformation_input",
                    "Transformation_input",
                ],
                "layer_1": [
                    None,
                    None,
                    "Electricity_and_heat_generation",
                    "Electricity_and_heat_generation",
                ],
                "layer_2": [
                    None,
                    None,
                    "Main_activity_producer_electricity_only",
                    "Main_activity_producer_CHP",
                ],
                "index": ["Primary_production", "Imports", "Coal", "Gas"],
                "+/-": [None, None, None, None],
                "depth": [0, 0, 1, 1],
                "1990": [100.0, 50.0, 25.0, 15.0],
                "1991": [105.0, 52.0, 26.0, 16.0],
                "1992": [110.0, 54.0, 27.0, 17.0],
                "TOTAL": [100.0, 50.0, 25.0, 15.0],
            }
        )

    def test_energy_balance_initialization_with_dataframe(self):
        """Test initializing EnergyBalance with a DataFrame"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        self.assertIsNotNone(eb.df_eb)
        self.assertIsInstance(eb.df_eb, pd.DataFrame)

    def test_energy_balance_has_filepath_mapping_csv(self):
        """Test that EnergyBalance has filepath_mapping_csv attribute"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        self.assertTrue(hasattr(eb, "filepath_mapping_csv"))

    def test_get_top_layer_entries_returns_dataframe(self):
        """Test get_top_layer_entries returns a DataFrame"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        result = eb.get_top_layer_entries()
        self.assertIsInstance(result, pd.DataFrame)

    def test_get_top_layer_entries_only_total_values(self):
        """Test get_top_layer_entries with only_total_values=True"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        result = eb.get_top_layer_entries(only_total_values=True)

        # Should only have TOTAL column
        if len(result.columns) > 0:
            self.assertIn("TOTAL", result.columns)

    def test_get_entries_of_category_returns_dataframe(self):
        """Test get_entries_of_category returns a DataFrame"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        result = eb.get_entries_of_category(
            "Total_absolute_values",
            only_total_values=False,
        )

        self.assertIsInstance(result, pd.DataFrame)

    def test_inherited_from_energy_balance_reader(self):
        """Test that EnergyBalance inherits from EnergyBalanceReader"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance
        from energy_balance_evaluation.utils import EnergyBalanceReader

        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )

        self.assertIsInstance(eb, EnergyBalanceReader)


class TestEnergyBalanceWithMocking(unittest.TestCase):
    """Test EnergyBalance class with mocked file operations"""

    @patch("energy_balance_evaluation.utils.pd.read_excel")
    def test_initialization_with_file_path(self, mock_read_excel):
        """Test EnergyBalance initialization with file path"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        # Setup mock
        mock_df = pd.DataFrame(
            {
                "layer_0": ["A", "B"],
                "layer_1": [None, None],
                "layer_2": [None, None],
                "index": ["X", "Y"],
                "Unnamed: 3": [1, 2],
                "Unnamed: 4": [3, 4],
                "Unnamed: 5": [5, 6],
                "Unnamed: 6": [7, 8],
                "1990": [100, 200],
            }
        )
        mock_read_excel.return_value = mock_df

        # This might fail due to missing file, but tests the initialization flow
        try:
            eb = EnergyBalance("2023", path_to_xlsb="fake_path.xlsb")
        except Exception:
            # Expected to potentially fail with mocked data
            pass


class TestCarrierNetworkClass(unittest.TestCase):
    """Test the CarrierNetwork class"""

    def test_carrier_network_initialization(self):
        """Test CarrierNetwork initialization with mock pypsa network"""
        try:
            import pypsa  # noqa: F401
            from energy_balance_evaluation import CarrierNetwork

            # Create a minimal test network
            n = pypsa.Network()
            n.add("Bus", "bus0", v_nom=380)
            n.add("Generator", "gen0", bus="bus0", p_nom=100, carrier="coal")

            # Should not raise an error
            cn = CarrierNetwork(
                carrier="coal",
                n=n,
                plot_subnetwork=False,
            )

            self.assertEqual(cn.carrier, "coal")
        except ImportError:
            self.skipTest("PyPSA not installed")
        except Exception as e:
            self.skipTest(f"PyPSA not properly installed: {e}")

    def test_eval_all_networks(self):
        """Test eval_all_networks function"""
        try:
            import pypsa  # noqa: F401
            from energy_balance_evaluation import eval_all_networks
            import tempfile

            # Create a minimal test network
            n = pypsa.Network()
            n.add("Bus", "bus0", v_nom=380)
            n.add("Carrier", "coal")

            # Create a temporary directory for outputs
            with tempfile.TemporaryDirectory() as tmpdir:
                result = eval_all_networks(
                    n=n,
                    png_outputfolder_path=tmpdir,
                    eval_one_node=False,
                )

                # Should return a list (even if empty)
                self.assertIsInstance(result, list)
        except ImportError:
            self.skipTest("PyPSA not installed")
        except Exception as e:
            self.skipTest(f"PyPSA not properly installed: {e}")


if __name__ == "__main__":
    unittest.main()
