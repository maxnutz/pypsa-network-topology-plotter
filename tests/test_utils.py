"""
Tests for utility functions and classes
"""

import unittest
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from io import StringIO


class TestExtractTrueKeys(unittest.TestCase):
    """Test the extract_true_keys function"""

    def test_extract_simple_dict_with_true(self):
        """Test extracting True keys from a simple dictionary"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'key1': True,
            'key2': False,
            'key3': True,
        }
        result = extract_true_keys(d)
        self.assertEqual(sorted(result), ['key1', 'key3'])

    def test_extract_nested_dict(self):
        """Test extracting True keys from nested dictionaries"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'parent1': {
                'child1': True,
                'child2': False,
            },
            'parent2': {
                'child3': True,
            }
        }
        result = extract_true_keys(d)
        self.assertIn('parent1>child1', result)
        self.assertIn('parent2>child3', result)
        self.assertNotIn('parent1>child2', result)

    def test_extract_with_nan_key(self):
        """Test that 'nan' keys are handled correctly"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'parent': {
                'nan': True,
                'child': True,
            }
        }
        result = extract_true_keys(d)
        self.assertIn('parent', result)  # 'nan' should be replaced with parent
        self.assertIn('parent>child', result)

    def test_extract_deeply_nested(self):
        """Test with deeply nested dictionaries"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'level1': {
                'level2': {
                    'level3': {
                        'key': True,
                    }
                }
            }
        }
        result = extract_true_keys(d)
        self.assertIn('level1>level2>level3>key', result)

    def test_extract_empty_dict(self):
        """Test with empty dictionary"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {}
        result = extract_true_keys(d)
        self.assertEqual(result, [])

    def test_extract_all_false(self):
        """Test dictionary with all False values"""
        from energy_balance_evaluation.utils import extract_true_keys
        
        d = {
            'key1': False,
            'key2': False,
            'nested': {
                'key3': False,
                'key4': False,
            }
        }
        result = extract_true_keys(d)
        self.assertEqual(result, [])


class TestReplaceByDict(unittest.TestCase):
    """Test the replace_by_dict function"""

    def test_simple_replacement(self):
        """Test simple string replacement"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "Hello world"
        replacement_dict = {'world': 'universe'}
        result = replace_by_dict(string, replacement_dict)
        self.assertEqual(result, "Hello universe")

    def test_multiple_replacements(self):
        """Test multiple replacements"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "foo bar foo baz"
        replacement_dict = {'foo': 'FOO', 'bar': 'BAR'}
        result = replace_by_dict(string, replacement_dict)
        self.assertEqual(result, "FOO BAR FOO baz")

    def test_no_matching_keys(self):
        """Test when no keys match"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "original string"
        replacement_dict = {'notfound': 'replacement'}
        result = replace_by_dict(string, replacement_dict)
        self.assertEqual(result, "original string")

    def test_empty_replacement_dict(self):
        """Test with empty replacement dictionary"""
        from energy_balance_evaluation.utils import replace_by_dict
        
        string = "original string"
        replacement_dict = {}
        result = replace_by_dict(string, replacement_dict)
        self.assertEqual(result, "original string")


class TestReadMappingCSV(unittest.TestCase):
    """Test the read_mapping_csv function"""

    def test_read_mapping_csv_basic(self):
        """Test reading a basic mapping CSV file"""
        from energy_balance_evaluation.utils import read_mapping_csv
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Category;PyPSA_Carrier\nCoal;coal\nGas;gas\n")
            f.flush()
            temp_path = f.name
        
        try:
            df = read_mapping_csv(temp_path)
            
            self.assertIsInstance(df, pd.DataFrame)
            self.assertEqual(len(df), 2)
            self.assertIn('Category', df.columns)
            self.assertIn('PyPSA_Carrier', df.columns)
        finally:
            os.unlink(temp_path)

    def test_read_mapping_csv_returns_dataframe(self):
        """Test that function returns a pandas DataFrame"""
        from energy_balance_evaluation.utils import read_mapping_csv
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Col1;Col2;Col3\n1;2;3\n4;5;6\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = read_mapping_csv(temp_path)
            self.assertIsInstance(result, pd.DataFrame)
        finally:
            os.unlink(temp_path)


class TestEnergyBalanceReader(unittest.TestCase):
    """Test the EnergyBalanceReader class"""

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

    def test_reader_initialization_with_dataframe(self):
        """Test initializing EnergyBalanceReader with a DataFrame"""
        from energy_balance_evaluation.utils import EnergyBalanceReader
        
        reader = EnergyBalanceReader(
            "2023",
            input_matrix=self._get_sample_df(),
        )
        
        self.assertIsNotNone(reader.df_eb)
        self.assertIsInstance(reader.df_eb, pd.DataFrame)

    def test_reader_has_expected_attributes(self):
        """Test that reader has expected attributes"""
        from energy_balance_evaluation.utils import EnergyBalanceReader
        
        reader = EnergyBalanceReader(
            "2023",
            input_matrix=self._get_sample_df(),
        )
        
        self.assertTrue(hasattr(reader, 'df_eb'))
        self.assertTrue(hasattr(reader, 'df_variables'))


if __name__ == '__main__':
    unittest.main()
