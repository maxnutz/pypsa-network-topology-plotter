"""
Test runner and configuration for the energy_balance_evaluation package
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def run_all_tests(verbosity=2):
    """
    Discover and run all tests in the tests directory
    
    Parameters:
    -----------
    verbosity : int
        The verbosity level for the test runner (0, 1, or 2)
    
    Returns:
    --------
    unittest.TestResult
        The result object containing information about the test run
    """
    # Discover all tests in the tests directory
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def run_specific_test(test_module, test_class=None, test_method=None, verbosity=2):
    """
    Run a specific test module, class, or method
    
    Parameters:
    -----------
    test_module : str
        Name of the test module (e.g., 'tests.test_imports')
    test_class : str, optional
        Name of the test class (e.g., 'TestPackageImports')
    test_method : str, optional
        Name of the test method (e.g., 'test_import_carrier_network')
    verbosity : int
        The verbosity level for the test runner (0, 1, or 2)
    
    Returns:
    --------
    unittest.TestResult
        The result object containing information about the test run
    """
    if test_method and test_class:
        test_name = f"{test_module}.{test_class}.{test_method}"
    elif test_class:
        test_name = f"{test_module}.{test_class}"
    else:
        test_name = test_module
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    # Run all tests
    result = run_all_tests(verbosity=2)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
