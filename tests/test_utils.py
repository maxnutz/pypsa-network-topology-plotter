"""
Tests for helpers in energy_balance_evaluation.utils.
"""

import unittest

import pypsa


class TestGetComponentsOfCarrier(unittest.TestCase):
    """Tests for the get_components_of_carrier utility function."""

    def _make_multi_component_network(self):
        """
        Network with 'gas' carrier on Generator, Load, Link, Store,
        StorageUnit and Bus, plus an 'electricity' carrier on Generator.
        """
        n = pypsa.Network()
        n.add("Carrier", "gas")
        n.add("Carrier", "electricity")

        n.add("Bus", "bus_gas", carrier="gas")
        n.add("Bus", "bus_elec", carrier="electricity")

        n.add("Generator", "gen_gas", bus="bus_gas", carrier="gas", p_nom=100)
        n.add(
            "Generator",
            "gen_elec",
            bus="bus_elec",
            carrier="electricity",
            p_nom=50,
        )
        n.add("Load", "load_gas", bus="bus_gas", carrier="gas", p_set=30)
        n.add(
            "Link",
            "link_gas",
            bus0="bus_gas",
            bus1="bus_elec",
            carrier="gas",
            p_nom=80,
        )
        n.add("Store", "store_gas", bus="bus_gas", carrier="gas", e_nom=200)
        n.add(
            "StorageUnit",
            "su_gas",
            bus="bus_gas",
            carrier="gas",
            p_nom=40,
        )
        return n

    def test_returns_dict(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIsInstance(result, dict)

    def test_generator_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("Generator", result)
        self.assertEqual(result["Generator"], 1)

    def test_load_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("Load", result)
        self.assertEqual(result["Load"], 1)

    def test_link_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("Link", result)
        self.assertEqual(result["Link"], 1)

    def test_store_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("Store", result)
        self.assertEqual(result["Store"], 1)

    def test_storage_unit_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("StorageUnit", result)
        self.assertEqual(result["StorageUnit"], 1)

    def test_bus_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        self.assertIn("Bus", result)
        self.assertEqual(result["Bus"], 1)

    def test_returns_integer_counts(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        for count in result.values():
            self.assertIsInstance(count, int)

    def test_other_carrier_count_not_included(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "gas")
        # electricity generator must NOT inflate the gas generator count
        self.assertEqual(result.get("Generator", 0), 1)

    def test_unknown_carrier_returns_empty_dict(self):
        from energy_balance_evaluation.utils import get_components_of_carrier

        n = self._make_multi_component_network()
        result = get_components_of_carrier(n, "unknown_carrier")
        self.assertEqual(result, {})
