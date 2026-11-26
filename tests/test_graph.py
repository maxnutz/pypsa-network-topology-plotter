"""
Tests for energy_balance_evaluation.graph.
"""

import pypsa
import pytest

from energy_balance_evaluation import CarrierTopology, InputError
from energy_balance_evaluation.graph import branch_ports, carrier_color


def _link_edges(graph):
    return [e for e in graph.edges if e.kind == "Link"]


def test_branch_ports_long_format(two_region_network: pypsa.Network) -> None:
    ports = branch_ports(two_region_network)
    smr = ports[ports["name"] == "R2 SMR"].sort_values("port")
    assert smr["port"].tolist() == [1, 2]
    assert smr["bus"].tolist() == ["R2 H2", "R2 co2 stored"]
    assert smr["efficiency"].tolist() == pytest.approx([0.76, -0.2])
    # single-port links have no bus2 row
    assert len(ports[ports["name"] == "R1 H2 Electrolysis"]) == 1
    assert "AC line R1-R2" in set(ports["name"])


def test_branch_ports_drops_unknown_bus(two_region_network: pypsa.Network) -> None:
    n = two_region_network
    n.add("Link", "dangling", bus0="R1 H2", bus1="R1 AC", carrier="x")
    n.links.loc["dangling", "bus1"] = "missing bus"
    assert "dangling" not in set(branch_ports(n)["name"])
    CarrierTopology(n, "H2", region="R1").build_graph()  # must not fail


def test_exact_carrier_match_with_suggestions(
    two_region_network: pypsa.Network,
) -> None:
    with pytest.raises(InputError, match="Did you mean: H2"):
        CarrierTopology(two_region_network, "H")


def test_negative_depth_rejected(two_region_network: pypsa.Network) -> None:
    with pytest.raises(InputError):
        CarrierTopology(two_region_network, "H2", depth=-1)


class TestAggregatedView:
    """No region: one node per bus carrier, union of all link types."""

    def test_one_node_per_bus_carrier(self, two_region_network: pypsa.Network) -> None:
        g = CarrierTopology(two_region_network, "H2").build_graph()
        bus_nodes = {k: v for k, v in g.nodes.items() if v.kind == "Bus"}
        assert set(bus_nodes) == {"bus|H2", "bus|AC", "bus|gas", "bus|co2 stored"}
        assert sorted(bus_nodes["bus|H2"].members) == ["R1 H2", "R2 H2"]
        assert bus_nodes["bus|H2"].is_start
        assert not bus_nodes["bus|AC"].is_start
        assert g.aggregated

    def test_union_of_link_types_across_regions(
        self, two_region_network: pypsa.Network
    ) -> None:
        # Electrolysis only in R1, SMR only in R2: both must appear.
        g = CarrierTopology(two_region_network, "H2").build_graph()
        carriers = {e.carrier for e in _link_edges(g)}
        assert carriers == {"H2 Electrolysis", "SMR", "H2 pipeline"}

    def test_pipeline_is_self_loop(self, two_region_network: pypsa.Network) -> None:
        g = CarrierTopology(two_region_network, "H2").build_graph()
        (pipe,) = [e for e in _link_edges(g) if e.carrier == "H2 pipeline"]
        assert pipe.source == pipe.target == "bus|H2"

    def test_multilink_ports_share_group(
        self, two_region_network: pypsa.Network
    ) -> None:
        g = CarrierTopology(two_region_network, "H2").build_graph()
        smr = sorted(
            (e for e in _link_edges(g) if e.carrier == "SMR"), key=lambda e: e.port
        )
        assert [(e.source, e.target, e.port) for e in smr] == [
            ("bus|gas", "bus|H2", 1),
            ("bus|gas", "bus|co2 stored", 2),
        ]
        assert len({e.group for e in smr}) == 1
        assert smr[1].efficiencies == pytest.approx([-0.2])

    def test_line_not_included_at_depth_1(
        self, two_region_network: pypsa.Network
    ) -> None:
        # the AC line does not touch an H2 bus
        g = CarrierTopology(two_region_network, "H2").build_graph()
        assert not [e for e in g.edges if e.kind == "Line"]

    def test_depth_2_reaches_line(self, two_region_network: pypsa.Network) -> None:
        g = CarrierTopology(two_region_network, "H2", depth=2).build_graph()
        assert [e for e in g.edges if e.kind == "Line"]

    def test_one_ports_aggregated(self, two_region_network: pypsa.Network) -> None:
        g = CarrierTopology(two_region_network, "H2").build_graph()
        gens = [v for v in g.nodes.values() if v.kind == "Generator"]
        assert len(gens) == 1
        # R1 gas is not connected to any H2 bus at depth 1, R2 gas is (SMR)
        assert gens[0].members == ["R2 gas gen"]
        assert gens[0].capacity == pytest.approx(10)
        kinds = {v.kind for v in g.nodes.values()}
        assert {"Load", "Store"} <= kinds


class TestRegionView:
    """Region given: detailed, every bus is its own node."""

    def test_location_match(self, two_region_network: pypsa.Network) -> None:
        t = CarrierTopology(two_region_network, "H2", region="R1")
        assert list(t.start_buses) == ["R1 H2"]

    def test_substring_fallback(self, two_region_network: pypsa.Network) -> None:
        # "R" is no location -> substring of the bus name -> both H2 buses
        t = CarrierTopology(two_region_network, "H2", region="R")
        assert sorted(t.start_buses) == ["R1 H2", "R2 H2"]

    def test_unknown_region(self, two_region_network: pypsa.Network) -> None:
        with pytest.raises(InputError, match="region"):
            CarrierTopology(two_region_network, "H2", region="XX")

    def test_detailed_includes_cross_region_bus(
        self, two_region_network: pypsa.Network
    ) -> None:
        g = CarrierTopology(two_region_network, "H2", region="R1").build_graph()
        bus_ids = {k for k, v in g.nodes.items() if v.kind == "Bus"}
        # R1 H2, its Electrolysis input R1 AC, and the pipeline end R2 H2
        assert bus_ids == {"bus|R1 H2", "bus|R1 AC", "bus|R2 H2"}
        assert {e.carrier for e in _link_edges(g)} == {"H2 Electrolysis", "H2 pipeline"}
        assert not g.aggregated

    def test_detailed_multilink_group_per_link(
        self, two_region_network: pypsa.Network
    ) -> None:
        g = CarrierTopology(two_region_network, "H2", region="R2").build_graph()
        smr = [e for e in _link_edges(g) if e.carrier == "SMR"]
        assert len(smr) == 2
        assert {e.group for e in smr} == {"Link|R2 SMR"}

    def test_depth_0_only_start_bus(self, two_region_network: pypsa.Network) -> None:
        g = CarrierTopology(
            two_region_network, "H2", region="R2", depth=0
        ).build_graph()
        assert {k for k, v in g.nodes.items() if v.kind == "Bus"} == {"bus|R2 H2"}
        assert not _link_edges(g)


def test_carrier_color() -> None:
    assert carrier_color("H2", {"H2": "#bf13a0"}) == "#bf13a0"
    fallback = carrier_color("unknown", {"unknown": ""})
    assert fallback.startswith("#")
    assert fallback == carrier_color("unknown", {})
