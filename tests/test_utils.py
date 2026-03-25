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


class TestCarriersNetworkBusPattern(unittest.TestCase):
    """Test bus_pattern filtering in CarriersNetwork."""

    def _make_network(self):
        """Network with two buses: bus_gas_AT0 and bus_gas_AT1."""
        n = pypsa.Network()
        n.add("Carrier", "gas")
        n.add("Bus", "bus_gas_AT0", carrier="gas")
        n.add("Bus", "bus_gas_AT1", carrier="gas")
        n.add("Generator", "gen_AT0", bus="bus_gas_AT0", carrier="gas", p_nom=100)
        n.add("Generator", "gen_AT1", bus="bus_gas_AT1", carrier="gas", p_nom=50)
        n.add("Load", "load_AT0", bus="bus_gas_AT0", carrier="gas", p_set=80)
        n.add(
            "Link",
            "link_AT0_AT1",
            bus0="bus_gas_AT0",
            bus1="bus_gas_AT1",
            carrier="gas",
            p_nom=60,
        )
        return n

    def test_bus_pattern_filters_buses(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n, bus_pattern="AT0")
        # Only AT0 bus should be present
        self.assertTrue(all("AT0" in idx for idx in cn.buses.index))

    def test_bus_pattern_filters_generators(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n, bus_pattern="AT0")
        # Only generator attached to AT0 bus
        self.assertEqual(len(cn.generators), 1)
        self.assertEqual(cn.generators.index[0], "gen_AT0")

    def test_bus_pattern_filters_loads(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n, bus_pattern="AT0")
        self.assertEqual(len(cn.loads), 1)
        self.assertEqual(cn.loads.index[0], "load_AT0")

    def test_bus_pattern_keeps_connected_links(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn = CarriersNetwork("gas", n, bus_pattern="AT0")
        # The link between AT0 and AT1 should still be visible
        self.assertFalse(cn.links.empty)

    def test_bus_pattern_no_match_raises(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        with self.assertRaises(Exception):
            CarriersNetwork("gas", n, bus_pattern="NONEXISTENT")

    def test_bus_pattern_mermaid_excludes_other_bus(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network()
        cn_full = CarriersNetwork("gas", n)
        cn_filtered = CarriersNetwork("gas", n, bus_pattern="AT0")
        mermaid_full = cn_full.get_mermaid_string()
        mermaid_filtered = cn_filtered.get_mermaid_string()
        # gen_AT1 should appear in full but not in filtered
        self.assertIn("gen_AT1", mermaid_full)
        self.assertNotIn("gen_AT1", mermaid_filtered)


class TestMultiLink(unittest.TestCase):
    """Test that bus3 / bus4 multilinks are fully handled."""

    def _make_network_with_multilink(self):
        """Network with a 4-port link (bus0..bus3) and a 5-port link (bus0..bus4)."""
        n = pypsa.Network()
        n.add("Carrier", "gas")
        for i in range(5):
            n.add("Bus", f"bus_gas_{i}", carrier="gas")

        # 4-port link: bus0, bus1, bus2, bus3
        n.add(
            "Link",
            "link_4port",
            bus0="bus_gas_0",
            bus1="bus_gas_1",
            bus2="bus_gas_2",
            bus3="bus_gas_3",
            carrier="gas",
            p_nom=100,
        )
        # 5-port link: bus0, bus1, bus2, bus3, bus4
        n.add(
            "Link",
            "link_5port",
            bus0="bus_gas_0",
            bus1="bus_gas_1",
            bus2="bus_gas_2",
            bus3="bus_gas_3",
            bus4="bus_gas_4",
            carrier="gas",
            p_nom=50,
        )
        return n

    def test_get_links_includes_bus3_and_bus4(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network_with_multilink()
        cn = CarriersNetwork("gas", n)
        self.assertFalse(cn.links.empty)
        self.assertIn("link_4port", cn.links.index)
        self.assertIn("link_5port", cn.links.index)

    def test_extra_bus_cols_detects_bus3_bus4(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network_with_multilink()
        cn = CarriersNetwork("gas", n)
        extra = cn._extra_bus_cols(cn.links)
        self.assertIn("bus2", extra)
        self.assertIn("bus3", extra)
        self.assertIn("bus4", extra)

    def test_mermaid_string_contains_bus3_and_bus4(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network_with_multilink()
        cn = CarriersNetwork("gas", n)
        mermaid = cn.get_mermaid_string()
        self.assertIn("bus_gas_3", mermaid)
        self.assertIn("bus_gas_4", mermaid)

    def test_mermaid_string_indirect_edge_label_for_bus3(self):
        from energy_balance_evaluation.utils import CarriersNetwork

        n = self._make_network_with_multilink()
        cn = CarriersNetwork("gas", n)
        mermaid = cn.get_mermaid_string()
        self.assertIn("indirect bus3", mermaid)
        self.assertIn("indirect bus4", mermaid)


if __name__ == "__main__":
    unittest.main()
