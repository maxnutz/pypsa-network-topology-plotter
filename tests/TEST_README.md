# Unit Tests for energy_balance_evaluation Package

This directory contains comprehensive unit tests for the `energy_balance_evaluation` package. The tests cover all major modules and functionality.

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── run_tests.py               # Test runner script
├── test_imports.py            # Tests for package imports
├── test_utils.py              # Tests for utility functions and classes
├── test_helpers.py            # Tests for helper functions
├── test_statics.py            # Tests for static data structures
├── test_energy_balance.py     # Tests for EnergyBalance and CarrierNetwork classes
├── test_integration.py        # Integration and end-to-end tests
└── README.md                  # This file
```

## Test Files Overview

### test_imports.py
Tests that verify all modules and functions are importable and have correct types.
- **TestPackageImports**: Tests for importing main classes and functions
  - `test_import_carrier_network`: Verify CarrierNetwork import
  - `test_import_utils`: Verify utility function imports
  - `test_import_statics`: Verify static data imports
  - `test_statics_dict_types`: Verify static data types
  - `test_statics_not_empty`: Verify static data is populated

### test_utils.py
Tests for utility functions and the EnergyBalanceReader class.
- **TestExtractTrueKeys**: Tests for the `extract_true_keys()` function
  - `test_extract_simple_dict_with_true`: Simple dictionary extraction
  - `test_extract_nested_dict`: Nested dictionary handling
  - `test_extract_with_nan_key`: Special 'nan' key handling
  - `test_extract_deeply_nested`: Deeply nested structures
  - `test_extract_empty_dict`: Empty dictionary handling
  - `test_extract_all_false`: Dictionary with all False values

- **TestReplaceByDict**: Tests for the `replace_by_dict()` function
  - `test_simple_replacement`: Single string replacement
  - `test_multiple_replacements`: Multiple replacements
  - `test_no_matching_keys`: When no keys match
  - `test_empty_replacement_dict`: Empty replacement dictionary

- **TestReadMappingCSV**: Tests for the `read_mapping_csv()` function
  - `test_read_mapping_csv_basic`: Basic CSV reading
  - `test_read_mapping_csv_returns_dataframe`: Return type validation

- **TestEnergyBalanceReader**: Tests for the EnergyBalanceReader class
  - `test_reader_initialization_with_dataframe`: Initialization with DataFrame
  - `test_reader_has_expected_attributes`: Check for required attributes

### test_helpers.py
Tests for the helper functions in _helpers.py.
- **TestProcessPypsaMappingToCSV**: Tests for `process_pypsa_mapping_to_csv()`
  - `test_process_mapping_with_default_sheet`: Default sheet processing
  - `test_process_mapping_with_custom_sheet`: Custom sheet name
  - `test_output_csv_filename`: Output filename derivation
  - `test_csv_separator_is_semicolon`: CSV separator verification
  - `test_index_not_written`: Index exclusion from CSV

### test_statics.py
Tests for static data structures defined in statics.py.
- **TestStaticsDataStructures**: Tests for individual static data structures
  - `test_rows_to_include_dict_structure`: Dictionary structure validation
  - `test_rows_to_include_dict_keys`: Expected keys verification
  - `test_rows_to_add_dict_structure`: List structure validation
  - `test_non_numerical_columns_list`: List content validation
  - `test_eb_row_string_replacement_dict`: String replacement dict validation

- **TestStaticsIntegration**: Integration tests for static data
  - `test_all_statics_are_importable`: All statics import together
  - `test_no_empty_statics`: Critical data is not empty

### test_energy_balance.py
Tests for the main EnergyBalance and CarrierNetwork classes.
- **TestEnergyBalanceClass**: Tests for EnergyBalance class
  - `test_energy_balance_initialization_with_dataframe`: Initialization
  - `test_get_top_layer_entries_returns_dataframe`: Data retrieval
  - `test_get_entries_of_category_returns_dataframe`: Category-based retrieval

- **TestEnergyBalanceWithMocking**: Tests with mocked file operations
  - `test_initialization_with_file_path`: File-based initialization

- **TestCarrierNetworkClass**: Tests for CarrierNetwork class
  - `test_carrier_network_initialization`: Network initialization
  - `test_eval_all_networks`: Multi-carrier evaluation

### test_integration.py
Integration and end-to-end tests combining multiple components.
- **TestIntegration**: Integration tests
  - `test_extract_true_keys_with_statics`: Using real static data
  - `test_workflow_read_mapping_and_extract`: Reading and extraction workflow
  - `test_statics_and_utils_together`: Utilities with statics

- **TestEdgeCases**: Edge case handling
  - `test_extract_true_keys_with_mixed_types`: Mixed data types
  - `test_replace_by_dict_special_characters`: Special character handling
  - `test_replace_by_dict_overlapping_keys`: Overlapping keys

- **TestDataStructureConsistency**: Data structure consistency
  - `test_non_numerical_columns_consistency`: Column naming conventions
  - `test_rows_to_add_dict_values_are_lists`: Type consistency

## Running the Tests

Run all tests using 

```bash
pixi run python -m pytest tests/ -v --tb=line 2>&1 | tail -100
``` 

### Using pytest

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_imports.py

# Run a specific test class
pytest tests/test_utils.py::TestExtractTrueKeys

# Run a specific test method
pytest tests/test_utils.py::TestExtractTrueKeys::test_extract_simple_dict_with_true

# Run with coverage report
pytest --cov=energy_balance_evaluation tests/
```

### Using the test runner script

```bash
# Run all tests from the package directory
python tests/run_tests.py

# Run with lower verbosity
python -c "from tests.run_tests import run_all_tests; run_all_tests(verbosity=1)"
```

## Test Dependencies

The tests use the following testing frameworks and libraries:

- **pytest**: Modern testing framework with fixtures
- **unittest**: Python's built-in testing framework
- **pytest-fixtures**: For test data fixtures
- **unittest.mock**: For mocking external dependencies

## Fixtures

The conftest.py file provides several pytest fixtures for testing:

### sample_energy_balance_df
Creates a sample energy balance DataFrame mimicking Eurostat structure with layers and data.

### sample_carrier_mapping_csv
Creates a sample carrier mapping DataFrame structure.

### mock_pypsa_network
Creates a minimal pypsa.Network object with basic structure (buses, generators, loads, lines).

### mock_pypsa_network_with_carriers
Creates a pypsa.Network with multiple carriers defined.

## Coverage

To generate a coverage report:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run -m pytest tests/

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
```

## Test Configuration

Configuration can be adjusted in:
- **pytest.ini**: Pytest configuration and markers
- **conftest.py**: Fixtures and pytest hooks
- **tests/run_tests.py**: Test runner configuration

## Continuous Integration

These tests are designed to be compatible with CI/CD pipelines. Use the provided test runner or pytest for integration with services like GitHub Actions, GitLab CI, or similar.

## Contributing

When adding new features to the package:

1. Write tests first (TDD approach)
2. Ensure all tests pass: `pytest`
3. Maintain or improve test coverage
4. Add or update fixtures in conftest.py as needed
5. Document test purpose in docstrings

## Common Issues

### ImportError when running tests
Make sure you're running tests from the package directory and the package is properly installed:
```bash
pip install -e .
```

### Module not found errors
Add the parent directory to your Python path or run tests from the correct directory.

### PyPSA not installed
Some tests are skipped if PyPSA is not installed. Install it with:
```bash
pip install pypsa
```

## Related Files

- [Main README](../README.md) - Package documentation
- [pyproject.toml](../pyproject.toml) - Package configuration
- [energy_balance_evaluation/__init__.py](../energy_balance_evaluation/__init__.py) - Package exports
