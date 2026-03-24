"""
Tests for CarriersNetwork in energy_balance_evaluation.utils.
"""

import unittest

import pypsa
import pytest


class TestCarriersNetworkInit(unittest.TestCase):
    """Test CarriersNetwork initialisation with a simple pypsa network."""

    def _make_network(self):
        n = pypsa.Network()
        n.add("Carrier", "gas")
        n.add("Bus", "bus_gas_0", carrier="gas")
        n.add("Bus", "bus_gas_1", carrier="gas")
        n.add("Generator", "gen_gas_0", bus="bus_gas_0", carrier="gas", p_nom=200)
        n.add("Load", "load_gas_1", bus="bus_gas_1", carrier="gas", p_set=100)
        n.add(
            "Link",
            "link_gas",
            bus0="bus_gas_0",
            bus1="bus_gas_1",
            carrier="gas",
            p_nom=150,
        )
        return n

    def test_initialization(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        self.assertEqual(cn.carrier, "gas")

    def test_buses_not_empty(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        self.assertFalse(cn.buses.empty)

    def test_generators_not_empty(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        self.assertFalse(cn.generators.empty)

    def test_loads_not_empty(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        self.assertFalse(cn.loads.empty)

    def test_links_not_empty(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        self.assertFalse(cn.links.empty)

    def test_no_buses_raises(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = pypsa.Network()
        n.add("Carrier", "wind")
        with self.assertRaises(Exception):
            CarriersNetwork("wind", n)

    def test_get_mermaid_string_returns_string(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        mermaid = cn.get_mermaid_string()
        self.assertIsInstance(mermaid, str)

    def test_get_mermaid_string_starts_with_flowchart(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        mermaid = cn.get_mermaid_string()
        self.assertTrue(mermaid.startswith("flowchart LR;"))

    def test_get_mermaid_string_contains_bus(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n)
        mermaid = cn.get_mermaid_string()
        self.assertIn("bus_gas_0", mermaid)


if __name__ == "__main__":
    unittest.main()
