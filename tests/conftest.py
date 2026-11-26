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


@pytest.fixture
def two_region_network():
    """
    Two regions (R1, R2) with buses for AC, H2, gas and co2 stored.

    * R1 H2 has Electrolysis (AC -> H2, bus2 heat-free), R2 H2 has SMR
      (gas -> H2, bus2 co2 stored with negative efficiency for testing).
    * An H2 pipeline connects R1 H2 -> R2 H2, an AC line R1 AC - R2 AC.
    * A gas generator sits on each gas bus, a load on R1 AC, a store on R2 H2.
    """
    n = pypsa.Network()
    for c in ["AC", "H2", "gas", "co2 stored"]:
        n.add("Carrier", c)
    n.carriers.loc["H2", "color"] = "#bf13a0"
    for r in ["R1", "R2"]:
        n.add("Bus", f"{r} AC", carrier="AC", location=r)
        n.add("Bus", f"{r} H2", carrier="H2", location=r)
        n.add("Bus", f"{r} gas", carrier="gas", location=r)
        n.add("Bus", f"{r} co2 stored", carrier="co2 stored", location=r)
        n.add("Generator", f"{r} gas gen", bus=f"{r} gas", carrier="gas", p_nom=10)
    n.add(
        "Link",
        "R1 H2 Electrolysis",
        bus0="R1 AC",
        bus1="R1 H2",
        carrier="H2 Electrolysis",
        efficiency=0.7,
        p_nom=5,
    )
    n.add(
        "Link",
        "R2 SMR",
        bus0="R2 gas",
        bus1="R2 H2",
        bus2="R2 co2 stored",
        carrier="SMR",
        efficiency=0.76,
        efficiency2=-0.2,
        p_nom=3,
    )
    n.add(
        "Link",
        "H2 pipeline R1 -> R2",
        bus0="R1 H2",
        bus1="R2 H2",
        carrier="H2 pipeline",
        efficiency=1.0,
        p_nom=2,
    )
    n.add(
        "Line",
        "AC line R1-R2",
        bus0="R1 AC",
        bus1="R2 AC",
        carrier="AC",
        s_nom=100,
        x=0.1,
    )
    n.add("Load", "R1 AC load", bus="R1 AC", carrier="AC", p_set=4)
    n.add("Store", "R2 H2 store", bus="R2 H2", carrier="H2", e_nom=50)
    return n
