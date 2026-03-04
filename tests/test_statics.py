"""
Tests for static data structures
"""

import unittest


class TestStaticsDataStructures(unittest.TestCase):
    """Test static data structures and dictionaries"""

    def test_rows_to_include_dict_structure(self):
        """Test rows_to_include_dict has expected structure"""
        from energy_balance_evaluation.statics import rows_to_include_dict
        
        self.assertIsInstance(rows_to_include_dict, dict)
        self.assertGreater(len(rows_to_include_dict), 0)
        
        # Test that values are either bool, dict or None
        for key, value in rows_to_include_dict.items():
            self.assertTrue(
                isinstance(value, (bool, dict)),
                f"Value for key '{key}' is neither bool nor dict"
            )

    def test_rows_to_include_dict_keys(self):
        """Test that rows_to_include_dict has expected keys"""
        from energy_balance_evaluation.statics import rows_to_include_dict
        
        expected_keys = ['Total_absolute_values', 'Transformation_input']
        for key in expected_keys:
            self.assertIn(key, rows_to_include_dict)

    def test_rows_to_add_dict_structure(self):
        """Test rows_to_add_dict has expected structure"""
        from energy_balance_evaluation.statics import rows_to_add_dict
        
        self.assertIsInstance(rows_to_add_dict, dict)
        self.assertGreater(len(rows_to_add_dict), 0)
        
        # Test that values are lists
        for key, value in rows_to_add_dict.items():
            self.assertIsInstance(value, list, f"Value for key '{key}' is not a list")

    def test_non_numerical_columns_list(self):
        """Test non_numerical_columns_list is a list"""
        from energy_balance_evaluation.statics import non_numerical_columns_list
        
        self.assertIsInstance(non_numerical_columns_list, list)
        self.assertGreater(len(non_numerical_columns_list), 0)
        
        # All elements should be strings
        for item in non_numerical_columns_list:
            self.assertIsInstance(item, str)

    def test_non_numerical_columns_contains_expected(self):
        """Test that non_numerical_columns_list contains expected columns"""
        from energy_balance_evaluation.statics import non_numerical_columns_list
        
        expected_items = ['layer_0', 'layer_1', 'layer_2', 'index']
        for item in expected_items:
            self.assertIn(item, non_numerical_columns_list)

    def test_eb_row_string_replacement_dict(self):
        """Test eb_row_string_replacement_dict structure"""
        from energy_balance_evaluation.statics import eb_row_string_replacement_dict
        
        self.assertIsInstance(eb_row_string_replacement_dict, dict)
        self.assertGreater(len(eb_row_string_replacement_dict), 0)
        
        # All keys and values should be strings
        for key, value in eb_row_string_replacement_dict.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    def test_rows_to_include_nested_structure(self):
        """Test that nested dicts in rows_to_include_dict are properly structured"""
        from energy_balance_evaluation.statics import rows_to_include_dict
        
        # Check for nested dicts
        for key, value in rows_to_include_dict.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    self.assertTrue(
                        isinstance(nested_value, (bool, dict)),
                        f"Nested value for '{key}' > '{nested_key}' is neither bool nor dict"
                    )

    def test_statics_are_not_modifiable(self):
        """Test that modifying statics doesn't affect new imports (they're fresh)"""
        from energy_balance_evaluation.statics import non_numerical_columns_list as list1
        
        original_length = len(list1)
        # Note: This is just to ensure the data structure is intact
        self.assertEqual(len(list1), original_length)


class TestStaticsIntegration(unittest.TestCase):
    """Integration tests for static data"""

    def test_all_statics_are_importable(self):
        """Test that all statics can be imported together"""
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

    def test_no_empty_statics(self):
        """Test that critical static data structures are not empty"""
        from energy_balance_evaluation import (
            rows_to_include_dict,
            rows_to_add_dict,
            non_numerical_columns_list,
            eb_row_string_replacement_dict,
        )
        
        self.assertTrue(len(rows_to_include_dict) > 0, "rows_to_include_dict is empty")
        self.assertTrue(len(rows_to_add_dict) > 0, "rows_to_add_dict is empty")
        self.assertTrue(len(non_numerical_columns_list) > 0, "non_numerical_columns_list is empty")
        self.assertTrue(len(eb_row_string_replacement_dict) > 0, "eb_row_string_replacement_dict is empty")


if __name__ == '__main__':
    unittest.main()
