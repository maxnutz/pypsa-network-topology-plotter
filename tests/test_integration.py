"""
Integration and end-to-end tests for energy_balance_evaluation
"""

import unittest
import pandas as pd
import tempfile
import os


class TestIntegration(unittest.TestCase):
    """Integration tests for the package"""

    def test_extract_true_keys_with_statics(self):
        """Test extract_true_keys with actual static data"""
        from energy_balance_evaluation import extract_true_keys, rows_to_include_dict

        # Use actual static data
        result = extract_true_keys(rows_to_include_dict)

        # Should return a non-empty list
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        # All elements should be strings
        for item in result:
            self.assertIsInstance(item, str)

    def test_workflow_read_mapping_and_extract(self):
        """Test workflow of reading mapping and extracting data"""
        from energy_balance_evaluation import read_mapping_csv

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Category;PyPSA_Carrier;Conversion\n")
            f.write("Coal;coal;1.0\n")
            f.write("Gas;gas;1.0\n")
            f.flush()
            temp_path = f.name

        try:
            df = read_mapping_csv(temp_path)
            self.assertEqual(len(df), 2)
            self.assertEqual(list(df.columns), ['Category', 'PyPSA_Carrier', 'Conversion'])
        finally:
            os.unlink(temp_path)

    def test_reduce_energy_balance_by_columns_integration(self):
        """Integration test for mapping CSV and reduce_energy_balance_by_columns.

        This test validates the full pipeline using the correct pypsa-entry/eb_index schema.
        """
        from energy_balance_evaluation import read_mapping_csv
        from energy_balance_evaluation.energy_balance_eval import EnergyBalance

        # Small numeric DataFrame whose columns match eb_index values
        # No need to include layer columns for this direct test
        data = pd.DataFrame(
            {
                "coal_primary": [1.0, 2.0],
                "coal_secondary": [3.0, 4.0],
                "gas": [5.0, 6.0],
            },
            index=["t0", "t1"],
        )

        # Mapping with pypsa-entry / eb_index schema, including many-to-one mappings
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("pypsa-entry;eb_index\n")
            f.write("coal;coal_primary\n")
            f.write("coal;coal_secondary\n")
            f.write("gas;gas\n")
            f.flush()
            mapping_path = f.name

        try:
            mapping_df = read_mapping_csv(mapping_path)

            # Create an EnergyBalance instance for access to the method
            sample_df = pd.DataFrame(
                {
                    "layer_0": ["A"],
                    "layer_1": [None],
                    "layer_2": [None],
                    "index": ["X"],
                    "var_name": ["X"],
                    "1990": [1.0],
                }
            )
            eb = EnergyBalance("2023", input_matrix=sample_df)

            # Run the reduction on our test data
            reduced = eb.reduce_energy_balance_by_columns(data, mapping_df)

            # We expect aggregation into pypsa-entry columns: coal = coal_primary + coal_secondary, gas unchanged
            self.assertListEqual(sorted(reduced.columns.tolist()), ["coal", "gas"])
            self.assertListEqual(reduced.index.tolist(), ["t0", "t1"])

            # Check numeric aggregation
            # t0: coal = 1 + 3 = 4, gas = 5
            # t1: coal = 2 + 4 = 6, gas = 6
            self.assertAlmostEqual(reduced.loc["t0", "coal"], 4.0)
            self.assertAlmostEqual(reduced.loc["t0", "gas"], 5.0)
            self.assertAlmostEqual(reduced.loc["t1", "coal"], 6.0)
            self.assertAlmostEqual(reduced.loc["t1", "gas"], 6.0)
        finally:
            os.unlink(mapping_path)

    def test_energy_balance_reader_with_prepared_dataframe(self):
        """Test EnergyBalanceReader with properly prepared DataFrame"""
        from energy_balance_evaluation.utils import EnergyBalanceReader

        sample_df = pd.DataFrame({
            'layer_0': ['Total_absolute_values', 'Total_absolute_values', 
                       'Transformation_input', 'Transformation_input'],
            'layer_1': [None, None, 'Electricity_and_heat_generation', 'Electricity_and_heat_generation'],
            'layer_2': [None, None, 'Main_activity_producer_electricity_only', 'Main_activity_producer_CHP'],
            'index': ['Primary_production', 'Imports', 'Coal', 'Gas'],
            '+/-': [None, None, None, None],
            'depth': [0, 0, 1, 1],
            '1990': [100.0, 50.0, 25.0, 15.0],
            'TOTAL': [100.0, 50.0, 25.0, 15.0],
        })

        reader = EnergyBalanceReader(
            "2023",
            input_matrix=sample_df,
        )

        # Should have processed the dataframe
        self.assertIsNotNone(reader.df_eb)
        self.assertIsNotNone(reader.df_variables)

    def test_statics_and_utils_together(self):
        """Test that statics and utils work together"""
        from energy_balance_evaluation import (
            extract_true_keys,
            rows_to_include_dict,
            rows_to_add_dict,
            eb_row_string_replacement_dict,
        )
        from energy_balance_evaluation.utils import replace_by_dict

        # Extract keys from statics
        included_keys = extract_true_keys(rows_to_include_dict)
        self.assertGreater(len(included_keys), 0)

        # Use replacement dict
        test_string = "Primary_production Imports"
        for key, value in list(eb_row_string_replacement_dict.items())[:3]:
            test_string = replace_by_dict(test_string, {key: value})

        self.assertIsInstance(test_string, str)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_extract_true_keys_with_mixed_types(self):
        """Test extract_true_keys handles mixed value types gracefully"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'bool_true': True,
            'bool_false': False,
            'nested': {
                'child_true': True,
                'child_false': False,
            },
            'empty_dict': {},
        }
        
        result = extract_true_keys(d)
        self.assertIn('bool_true', result)
        self.assertIn('nested>child_true', result)
        self.assertNotIn('bool_false', result)
        self.assertNotIn('nested>child_false', result)

    def test_replace_by_dict_special_characters(self):
        """Test replace_by_dict with special characters"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "test-with_special.chars"
        replacement_dict = {
            '-': '_',
            '.': '_',
        }
        
        result = replace_by_dict(string, replacement_dict)
        self.assertEqual(result, "test_with_special_chars")

    def test_replace_by_dict_overlapping_keys(self):
        """Test replace_by_dict with overlapping replacement keys"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "aaa"
        replacement_dict = {
            'aa': 'b',
            'a': 'x',
        }
        
        # Order matters in dict iteration
        result = replace_by_dict(string, replacement_dict)
        self.assertIsInstance(result, str)


class TestDataStructureConsistency(unittest.TestCase):
    """Test consistency of data structures"""

    def test_non_numerical_columns_consistency(self):
        """Test that non_numerical_columns are properly structured"""
        from energy_balance_evaluation.statics import non_numerical_columns_list
        
        # All elements should be strings
        for col in non_numerical_columns_list:
            self.assertIsInstance(col, str)

    def test_rows_to_add_dict_values_are_lists(self):
        """Test that all values in rows_to_add_dict are lists"""
        from energy_balance_evaluation.statics import rows_to_add_dict
        
        for key, value in rows_to_add_dict.items():
            self.assertIsInstance(value, list, f"Value for key '{key}' is not a list")
            
            # All list elements should be strings
            for item in value:
                self.assertIsInstance(item, str)

    def test_replacement_dict_no_empty_keys_or_values(self):
        """Test that replacement dict has no empty keys or values"""
        from energy_balance_evaluation.statics import eb_row_string_replacement_dict
        
        for key, value in eb_row_string_replacement_dict.items():
            self.assertGreater(len(key), 0, "Empty key found in replacement dict")
            self.assertGreater(len(value), 0, "Empty value found in replacement dict")


if __name__ == '__main__':
    unittest.main()
