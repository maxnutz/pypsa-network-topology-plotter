"""
Pytest configuration and fixtures for energy_balance_evaluation package tests
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_energy_balance_df():
    """
    Create a sample energy balance DataFrame mimicking Eurostat structure
    """
    data = {
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
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_carrier_mapping_csv():
    """
    Create a sample carrier mapping CSV structure
    """
    data = {
        'Energy_Balance_Category': ['Coal', 'Natural_Gas', 'Electricity'],
        'PyPSA_Carrier': ['coal', 'gas', 'ac'],
        'Conversion': [1.0, 1.0, 1.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_pypsa_network():
    """
    Create a mock pypsa.Network object with minimal structure
    """
    try:
        import pypsa
        
        # Create a minimal network
        n = pypsa.Network()
        
        # Add some buses
        n.add("Bus", "bus0", v_nom=380)
        n.add("Bus", "bus1", v_nom=380)
        
        # Add a generator
        n.add(
            "Generator",
            "gen0",
            bus="bus0",
            p_nom=100,
            carrier="coal",
        )
        
        # Add a load
        n.add(
            "Load",
            "load0",
            bus="bus1",
            p_set=50,
            carrier="electricity",
        )
        
        # Add a line
        n.add(
            "Line",
            "line0",
            bus0="bus0",
            bus1="bus1",
            x=0.1,
            r=0.01,
        )
        
        return n
    except ImportError:
        pytest.skip("pypsa not installed")


@pytest.fixture
def mock_pypsa_network_with_carriers():
    """
    Create a mock pypsa.Network with multiple carriers
    """
    try:
        import pypsa
        
        n = pypsa.Network()
        
        # Add multiple buses with different carriers
        for carrier in ['coal', 'gas', 'electricity']:
            n.add("Bus", f"bus_{carrier}", v_nom=380, carrier=carrier)
        
        # Add carriers to the network
        n.add("Carrier", "coal")
        n.add("Carrier", "gas")
        n.add("Carrier", "electricity")
        
        return n
    except ImportError:
        pytest.skip("pypsa not installed")
