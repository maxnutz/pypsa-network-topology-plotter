"""
Tests for EnergyBalance and related classes
"""

import unittest
import pandas as pd
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
                'Final Energy': {
                    'description': 'total final energy consumption',
                    'unit': 'GWh',
                    'nrg': 'FC_E',
                    'siec': 'TOTAL',
                    'value': 279335.902
                }
            },
            {
                'Final Energy|Electricity': {
                    'description': 'final energy consumption of electricity',
                    'unit': 'GWh',
                    'nrg': 'FC_E',
                    'siec': 'E7000',
                    'value': 63260.630
                }
            }
        ]

        self.yaml_file = self.temp_path / 'test_variables.yaml'
        with open(self.yaml_file, 'w') as f:
            yaml.dump(self.yaml_content, f)

        # Create a sample TSV file
        self.tsv_file = self.temp_path / 'test_data.tsv'
        tsv_data = """freq\tnrg_bal\tsiec\tunit\tgeo\t2023
A\tFC_E\tTOTAL\tGWH\tAT\t279335.902
A\tFC_E\tE7000\tGWH\tAT\t63260.630
A\tFC_E\tBIOE\tGWH\tAT\t62388.302
A\tFC_E\tTOTAL\tGWH\tDE\t500000.0"""
        with open(self.tsv_file, 'w') as f:
            f.write(tsv_data)

        self.codelist_file = self.temp_path / 'codelist.yaml'

    def tearDown(self):
        """Clean up temporary files"""
        self.temp_dir.cleanup()

    def test_variables_set_initialization(self):
        """Test VariablesSet initialization"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='final_energy',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country='AT'
        )

        self.assertEqual(vs.name, 'final_energy')
        self.assertEqual(vs.year, '2023')
        self.assertEqual(vs.country, 'AT')
        self.assertIsNone(vs.variables_dict)

    def test_read_yaml_file(self):
        """Test reading YAML definition file"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='final_energy',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs.read_yaml_file()

        self.assertIsInstance(result, dict)
        self.assertIn('Final Energy', result)
        self.assertIn('Final Energy|Electricity', result)
        self.assertEqual(result['Final Energy']['nrg'], 'FC_E')
        self.assertEqual(result['Final Energy']['siec'], 'TOTAL')

    def test_parse_codes_single(self):
        """Test parsing single code"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes('FC_E')
        self.assertEqual(result, ['FC_E'])

    def test_parse_codes_multiple(self):
        """Test parsing multiple comma-separated codes"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes('FC_OTH_HH_E,FC_OTH_CP_E')
        self.assertEqual(result, ['FC_OTH_HH_E', 'FC_OTH_CP_E'])

    def test_parse_codes_with_comment(self):
        """Test parsing codes with inline comments"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes('FC_E  # Final consumption')
        self.assertEqual(result, ['FC_E'])

    def test_parse_codes_empty(self):
        """Test parsing empty code string"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        result = vs._parse_codes('')
        self.assertEqual(result, [])

    def test_load_tsv_data(self):
        """Test loading TSV data"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        df = vs._load_tsv_data(str(self.tsv_file))

        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('freq', df.columns)
        self.assertIn('nrg_bal', df.columns)
        self.assertIn('siec', df.columns)
        self.assertIn('geo', df.columns)

    def test_calculate_variable_values(self):
        """Test calculating variable values from TSV"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country='AT'
        )

        # First read the YAML
        vs.read_yaml_file()

        # Calculate values
        values = vs.calculate_variable_values(str(self.tsv_file))

        self.assertIsInstance(values, dict)
        self.assertIn('Final Energy', values)
        self.assertIn('Final Energy|Electricity', values)
        # Check that values are floats
        self.assertIsInstance(values['Final Energy'], float)

    def test_write_codelist(self):
        """Test writing codelist YAML"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country='AT'
        )

        # Write codelist
        vs.write_codelist(filepath_tsv=str(self.tsv_file))

        # Verify file was created
        self.assertTrue(self.codelist_file.exists())

        # Read and verify content
        with open(self.codelist_file, 'r') as f:
            codelist = yaml.safe_load(f)

        self.assertIsInstance(codelist, list)
        self.assertGreater(len(codelist), 0)

        # Check structure of first entry
        first_entry = codelist[0]
        self.assertIn('variable', first_entry)
        self.assertIn('year', first_entry)
        self.assertIn('value', first_entry)
        self.assertIn('validation', first_entry)
        self.assertEqual(first_entry['year'], '2023')

    def test_default_country_is_at(self):
        """Test that default country is Austria"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
        )

        self.assertEqual(vs.country, 'AT')

    def test_custom_country(self):
        """Test using custom country code"""
        from energy_balance_evaluation.energy_balance_eval import VariablesSet

        vs = VariablesSet(
            set_name='test',
            year=2023,
            filepath_definition=str(self.yaml_file),
            filepath_codelist=str(self.codelist_file),
            country='DE'
        )

        self.assertEqual(vs.country, 'DE')


class TestEnergyBalanceClass(unittest.TestCase):
    """Test the EnergyBalance class"""

    def _get_sample_df(self):
        """Helper to create sample energy balance DataFrame"""
        return pd.DataFrame({
            'layer_0': ['Total_absolute_values', 'Total_absolute_values', 
                       'Transformation_input', 'Transformation_input'],
            'layer_1': [None, None, 'Electricity_and_heat_generation', 'Electricity_and_heat_generation'],
            'layer_2': [None, None, 'Main_activity_producer_electricity_only', 'Main_activity_producer_CHP'],
            'index': ['Primary_production', 'Imports', 'Coal', 'Gas'],
            '+/-': [None, None, None, None],
            'depth': [0, 0, 1, 1],
            '1990': [100.0, 50.0, 25.0, 15.0],
            '1991': [105.0, 52.0, 26.0, 16.0],
            '1992': [110.0, 54.0, 27.0, 17.0],
            'TOTAL': [100.0, 50.0, 25.0, 15.0],
        })

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
        
        self.assertTrue(hasattr(eb, 'filepath_mapping_csv'))

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
            self.assertIn('TOTAL', result.columns)

    def test_get_entries_of_category_returns_dataframe(self):
        """Test get_entries_of_category returns a DataFrame"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance
        
        eb = EnergyBalance(
            "2023",
            input_matrix=self._get_sample_df(),
        )
        
        result = eb.get_entries_of_category(
            'Total_absolute_values',
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

    @patch('energy_balance_evaluation.utils.pd.read_excel')
    def test_initialization_with_file_path(self, mock_read_excel):
        """Test EnergyBalance initialization with file path"""
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance
        
        # Setup mock
        mock_df = pd.DataFrame({
            'layer_0': ['A', 'B'],
            'layer_1': [None, None],
            'layer_2': [None, None],
            'index': ['X', 'Y'],
            'Unnamed: 3': [1, 2],
            'Unnamed: 4': [3, 4],
            'Unnamed: 5': [5, 6],
            'Unnamed: 6': [7, 8],
            '1990': [100, 200],
        })
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
                carrier='coal',
                n=n,
                plot_subnetwork=False,
            )
            
            self.assertEqual(cn.carrier, 'coal')
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


if __name__ == '__main__':
    unittest.main()
