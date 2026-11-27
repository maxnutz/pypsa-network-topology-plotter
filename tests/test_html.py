"""
Tests for energy_balance_evaluation.html_export.
"""

import json
import re
from pathlib import Path

import pypsa

from energy_balance_evaluation import CarrierTopology, plot_carrier_topology
from energy_balance_evaluation.graph import Edge
from energy_balance_evaluation.html_export import (
    efficiency_text,
    output_filename,
    topology_html,
)


def _dataset(html: str, name: str) -> list[dict]:
    match = re.search(rf"{name} = new vis\.DataSet\((\[.*?\])\);", html, re.S)
    assert match, f"{name} DataSet not found"
    return json.loads(match.group(1))


def test_efficiency_text_signed() -> None:
    edge = Edge("a", "b", "Link", "SMR", "g", port=2, efficiencies=[-0.2])
    assert efficiency_text(edge) == "η2=-0.2"
    edge1 = Edge("a", "b", "Link", "SMR", "g", port=1, efficiencies=[0.7, 0.8])
    assert efficiency_text(edge1) == "η=+0.7…+0.8"
    assert efficiency_text(Edge("a", "b", "Line", "AC", "g", port=1)) == ""


def test_output_filename() -> None:
    assert output_filename("H2") == "H2.html"
    assert output_filename("co2 stored", "AT11") == "co2_stored_AT11.html"


def test_html_contains_groups_and_labels(two_region_network: pypsa.Network) -> None:
    g = CarrierTopology(two_region_network, "H2").build_graph()
    html = topology_html(g)
    edges = _dataset(html, "edges")
    smr = [e for e in edges if e["linkgroup"] == "Link|SMR"]
    assert len(smr) == 2
    assert all(e["arrows"] == "to" for e in smr)
    assert {e["color"] for e in smr} == {smr[0]["color"]}, "one colour per multilink"
    assert any("η2=-0.2" in e["label"] for e in smr)
    assert all("(n=1)" in e["label"] for e in smr)
    # self-loop of the pipeline gets its own selfReference settings
    (pipe,) = [e for e in edges if e["linkgroup"] == "Link|H2 pipeline"]
    assert pipe["from"] == pipe["to"] and "selfReference" in pipe
    nodes = _dataset(html, "nodes")
    h2 = next(n for n in nodes if n["id"] == "bus|H2")
    assert h2["color"] == "#bf13a0"
    assert h2["borderWidth"] > 1
    # hover script injected after the graph is drawn
    assert html.index("drawGraph();") < html.index('network.on("hoverEdge"')


def test_parallel_edges_are_curved(two_region_network: pypsa.Network) -> None:
    n = two_region_network
    n.add(
        "Link",
        "R1 H2 Fuel Cell",
        bus0="R1 H2",
        bus1="R1 AC",
        carrier="H2 Fuel Cell",
        efficiency=0.5,
    )
    html = topology_html(CarrierTopology(n, "H2").build_graph())
    edges = _dataset(html, "edges")
    between = [e for e in edges if {e["from"], e["to"]} == {"bus|H2", "bus|AC"}]
    assert len(between) == 2
    assert all("smooth" in e for e in between)


def test_plot_carrier_topology_writes_file(
    two_region_network: pypsa.Network, tmp_path: Path
) -> None:
    path = plot_carrier_topology(
        two_region_network, "H2", region="R1", output_dir=tmp_path
    )
    assert path == tmp_path / "H2_R1.html"
    content = path.read_text(encoding="utf-8")
    assert "region &#x27;R1&#x27;" in content
    assert (
        "cdnjs.cloudflare.com/ajax/libs/vis-network" not in content
    ), "vis-network is inlined"


def test_tooltips_are_plain_text(two_region_network: pypsa.Network) -> None:
    """Network-controlled names cannot inject markup into the page."""
    evil = '</script><img src=x onerror="alert(1)">'
    n = two_region_network
    n.add("Store", evil, bus="R2 H2", carrier="H2", e_nom=1)
    html = topology_html(CarrierTopology(n, "H2").build_graph())
    # the data JSON escapes '<', '>' so the name cannot close the <script>
    assert evil not in html and "<img" not in html
    nodes = _dataset(html, "nodes")
    assert any(evil in node["title"] for node in nodes)
    # vis-network shows string titles via innerText, never as HTML
    assert "this.frame.innerText=t" in html
