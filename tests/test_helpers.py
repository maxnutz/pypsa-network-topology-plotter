"""
Tests for helper functions
"""

import unittest
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os


class TestProcessPypsaMappingToCSV(unittest.TestCase):
    """Test the process_pypsa_mapping_to_csv function"""

    @patch('pandas.read_excel')
    @patch('pandas.DataFrame.to_csv')
    def test_process_mapping_with_default_sheet(self, mock_to_csv, mock_read_excel):
        """Test processing mapping file with default sheet name"""
        from energy_balance_evaluation._helpers import process_pypsa_mapping_to_csv
        
        # Setup mocks
        test_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_read_excel.return_value = test_df
        
        # Call function
        process_pypsa_mapping_to_csv("/path/to/mapping.ods")
        
        # Assertions
        mock_read_excel.assert_called_once()
        mock_to_csv.assert_called_once()

    @patch('pandas.read_excel')
    @patch('pandas.DataFrame.to_csv')
    def test_process_mapping_with_custom_sheet(self, mock_to_csv, mock_read_excel):
        """Test processing mapping file with custom sheet name"""
        from energy_balance_evaluation._helpers import process_pypsa_mapping_to_csv
        
        # Setup mocks
        test_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_read_excel.return_value = test_df
        
        # Call function with custom sheet
        process_pypsa_mapping_to_csv(
            "/path/to/mapping.ods",
            sheet_name="custom_sheet"
        )
        
        # Assertions
        call_args = mock_read_excel.call_args
        self.assertEqual(call_args[1]['sheet_name'], 'custom_sheet')
        mock_to_csv.assert_called_once()

    @patch('pandas.read_excel')
    @patch('pandas.DataFrame.to_csv')
    def test_output_csv_filename(self, mock_to_csv, mock_read_excel):
        """Test that output CSV filename is correctly derived from input"""
        from energy_balance_evaluation._helpers import process_pypsa_mapping_to_csv
        
        # Setup mocks
        test_df = pd.DataFrame({'col1': [1, 2]})
        mock_read_excel.return_value = test_df
        
        # Call function
        process_pypsa_mapping_to_csv("/path/to/mapping.ods")
        
        # Check that to_csv was called with correct path
        call_args = mock_to_csv.call_args[0]
        self.assertTrue(call_args[0].endswith('.csv'))
        self.assertIn('mapping', call_args[0])

    @patch('pandas.read_excel')
    @patch('pandas.DataFrame.to_csv')
    def test_csv_separator_is_semicolon(self, mock_to_csv, mock_read_excel):
        """Test that CSV separator is set to semicolon"""
        from energy_balance_evaluation._helpers import process_pypsa_mapping_to_csv
        
        # Setup mocks
        test_df = pd.DataFrame({'col1': [1, 2]})
        mock_read_excel.return_value = test_df
        
        # Call function
        process_pypsa_mapping_to_csv("/path/to/mapping.ods")
        
        # Check that to_csv was called with semicolon separator
        call_args = mock_to_csv.call_args[1]
        self.assertEqual(call_args['sep'], ';')

    @patch('pandas.read_excel')
    @patch('pandas.DataFrame.to_csv')
    def test_index_not_written(self, mock_to_csv, mock_read_excel):
        """Test that index is not written to CSV"""
        from energy_balance_evaluation._helpers import process_pypsa_mapping_to_csv
        
        # Setup mocks
        test_df = pd.DataFrame({'col1': [1, 2]})
        mock_read_excel.return_value = test_df
        
        # Call function
        process_pypsa_mapping_to_csv("/path/to/mapping.ods")
        
        # Check that to_csv was called with index=False
        call_args = mock_to_csv.call_args[1]
        self.assertEqual(call_args['index'], False)


if __name__ == '__main__':
    unittest.main()
