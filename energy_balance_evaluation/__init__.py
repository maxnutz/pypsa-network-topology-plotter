"""
This package contains a set of tools for evaluating energy balances and pypsa networks.

The following classes and functions are available:

- `EnergyBalance`: Class for evaluating the energy balance data
- `CarrierNetwork`: Class for evaluating the pypsa-network per carrier
- `eval_all_networks`: Function for evaluating given network for all carriers in the respective network
- `extract_true_keys`: Function for extracting keys from a dictionary where the value is True
- `rows_to_include_dict`: Dictionary of rows to include for the light version of the energy balance
- `rows_to_add_dict`: Dictionary of rows to add together for the light version of the energy balance
- `non_numerical_columns_list`: List of non-numerical columns in eurostat energy balance matrix
"""

# from energy_balance_evaluation.energy_balance_eval import EnergyBalance
from energy_balance_evaluation.pypsa_network_eval import (
    CarrierNetwork,
    eval_all_networks,
)
from energy_balance_evaluation.utils import extract_true_keys, read_mapping_csv
from energy_balance_evaluation.statics import (
    rows_to_add_dict,
    rows_to_include_dict,
    non_numerical_columns_list,
    eb_row_string_replacement_dict,
)

__all__ = [
    # "EnergyBalance",
    "CarrierNetwork",
    "eval_all_networks",
    "extract_true_keys",
    "read_mapping_csv",
    "rows_to_include_dict",
    "rows_to_add_dict",
    "non_numerical_columns_list",
    "eb_row_string_replacement_dict",
]
