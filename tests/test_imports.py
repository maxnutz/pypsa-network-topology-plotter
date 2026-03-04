"""
Tests for package imports and module structure
"""

import unittest
import sys
import os


class TestPackageImports(unittest.TestCase):
    """Test that all modules are importable"""

    def test_import_carrier_network(self):
        """Test import of CarrierNetwork and eval_all_networks"""
        from energy_balance_evaluation import CarrierNetwork, eval_all_networks
        self.assertIsNotNone(CarrierNetwork)
        self.assertIsNotNone(eval_all_networks)

    def test_import_utils(self):
        """Test import of utility functions"""
        from energy_balance_evaluation import extract_true_keys, read_mapping_csv
        self.assertIsNotNone(extract_true_keys)
        self.assertIsNotNone(read_mapping_csv)

    def test_import_statics(self):
        """Test import of static data"""
        from energy_balance_evaluation import (
            rows_to_include_dict,
            rows_to_add_dict,
            non_numerical_columns_list,
            eb_row_string_replacement_dict,
        )
        self.assertIsNotNone(rows_to_include_dict)
        self.assertIsNotNone(rows_to_add_dict)
        self.assertIsNotNone(non_numerical_columns_list)
        self.assertIsNotNone(eb_row_string_replacement_dict)

    def test_statics_dict_types(self):
        """Test that static dicts and lists have correct types"""
        from energy_balance_evaluation import (
            rows_to_include_dict,
            rows_to_add_dict,
            non_numerical_columns_list,
            eb_row_string_replacement_dict,
        )
        
        self.assertIsInstance(rows_to_include_dict, dict)
        self.assertIsInstance(rows_to_add_dict, dict)
        self.assertIsInstance(non_numerical_columns_list, list)
        self.assertIsInstance(eb_row_string_replacement_dict, dict)

    def test_statics_not_empty(self):
        """Test that static data is not empty"""
        from energy_balance_evaluation import (
            rows_to_include_dict,
            rows_to_add_dict,
            non_numerical_columns_list,
            eb_row_string_replacement_dict,
        )
        
        self.assertTrue(len(rows_to_include_dict) > 0)
        self.assertTrue(len(rows_to_add_dict) > 0)
        self.assertTrue(len(non_numerical_columns_list) > 0)
        self.assertTrue(len(eb_row_string_replacement_dict) > 0)


if __name__ == '__main__':
    unittest.main()
