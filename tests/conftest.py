"""
Pytest configuration and fixtures for energy_balance_evaluation tests.
"""

import pytest
import pypsa


@pytest.fixture
def simple_network():
    """
    A minimal pypsa.Network with two buses, a generator, a load and a link,
    all using the 'coal' carrier.
    """
    n = pypsa.Network()

    n.add("Carrier", "coal")

    n.add("Bus", "bus_coal_0", carrier="coal")
    n.add("Bus", "bus_coal_1", carrier="coal")

    n.add("Generator", "gen_coal_0", bus="bus_coal_0", carrier="coal", p_nom=100)

    n.add("Load", "load_coal_1", bus="bus_coal_1", carrier="coal", p_set=50)

    n.add(
        "Link",
        "link_coal",
        bus0="bus_coal_0",
        bus1="bus_coal_1",
        carrier="coal",
        p_nom=80,
    )

    return n
