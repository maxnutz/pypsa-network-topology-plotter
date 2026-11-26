"""
energy_balance_evaluation
=========================
Interactive HTML topology plots of pypsa networks around a carrier.

Available classes and functions
--------------------------------
- ``plot_carrier_topology`` – build the topology around a carrier and write it
                              as interactive HTML.
- ``CarrierTopology``       – select the sub-network around a carrier and build
                              a plot-independent ``TopologyGraph``.
- ``write_topology_html``   – render a ``TopologyGraph`` as HTML.
- ``eval_all_networks``     – write an aggregated plot for every bus carrier.
- ``get_components_of_carrier`` – count components per type using a carrier.
"""

from energy_balance_evaluation.graph import CarrierTopology, TopologyGraph
from energy_balance_evaluation.html_export import write_topology_html
from energy_balance_evaluation.pypsa_network_eval import (
    eval_all_networks,
    plot_carrier_topology,
)
from energy_balance_evaluation.utils import InputError, get_components_of_carrier

__all__ = [
    "CarrierTopology",
    "InputError",
    "TopologyGraph",
    "eval_all_networks",
    "get_components_of_carrier",
    "plot_carrier_topology",
    "write_topology_html",
]
