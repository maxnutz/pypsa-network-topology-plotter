"""
html_export – render a :class:`~energy_balance_evaluation.graph.TopologyGraph`
as an interactive, self-contained HTML file using pyvis (vis-network).

Hovering a node highlights it, its edges and all lines of the (multi)links it
is part of. Hovering a line highlights every line of the same (multi)link and
the buses it connects.
"""

from __future__ import annotations

import html
import math
import re
from collections import defaultdict
from pathlib import Path

from pyvis.network import Network

from .graph import Edge, Node, TopologyGraph, carrier_color

#: Maximum number of member names listed in a tooltip.
MAX_TOOLTIP_MEMBERS = 15

_NODE_SHAPES: dict[str, str] = {
    "Bus": "dot",
    "Generator": "triangle",
    "Load": "triangleDown",
    "Store": "square",
    "StorageUnit": "diamond",
}

_OPTIONS: dict = {
    "interaction": {
        "hover": True,
        "tooltipDelay": 120,
        "navigationButtons": True,
        "keyboard": True,
        "multiselect": True,
    },
    "physics": {
        "enabled": True,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
            "gravitationalConstant": -150,
            "centralGravity": 0.01,
            "springLength": 180,
            "springConstant": 0.05,
            "avoidOverlap": 0.6,
        },
        "stabilization": {"enabled": True, "iterations": 800},
    },
    "edges": {
        "font": {"size": 11, "align": "middle", "strokeWidth": 4},
        "smooth": {"enabled": True, "type": "dynamic"},
        "selectionWidth": 2,
    },
    "nodes": {"font": {"size": 15}},
}

_CSS = """
<style>
  .vis-tooltip { white-space: pre-line !important; max-width: 520px;
                 font-family: monospace; font-size: 12px; }
  #topology-header { font-family: sans-serif; padding: 8px 16px; }
  #topology-header h2 { margin: 0 0 4px 0; font-size: 20px; }
  #topology-header p { margin: 2px 0; font-size: 13px; color: #444; }
</style>
"""

_HIGHLIGHT_JS = """
<script>
(function () {
  if (typeof network === "undefined" || network === null) { return; }
  var DIM_NODE = "rgba(200,200,200,0.35)";
  var DIM_FONT = "rgba(140,140,140,0.35)";
  var origNodes = {}, origEdges = {}, groups = {};
  nodes.get().forEach(function (n) { origNodes[n.id] = {color: n.color, font: n.font}; });
  edges.get().forEach(function (e) {
    origEdges[e.id] = {color: e.color, font: e.font, width: e.width};
    (groups[e.linkgroup] = groups[e.linkgroup] || []).push(e.id);
  });
  var active = false;
  function groupOf(edgeId) {
    var e = edges.get(edgeId);
    return (e && groups[e.linkgroup]) ? groups[e.linkgroup] : [edgeId];
  }
  function highlight(edgeIds, nodeIds) {
    var ns = new Set(nodeIds), es = new Set(edgeIds);
    edgeIds.forEach(function (id) {
      var e = edges.get(id); if (e) { ns.add(e.from); ns.add(e.to); }
    });
    nodes.update(Object.keys(origNodes).map(function (id) {
      var o = origNodes[id];
      return ns.has(id) ? {id: id, color: o.color, font: o.font}
                        : {id: id, color: DIM_NODE, font: {color: DIM_FONT}};
    }));
    edges.update(Object.keys(origEdges).map(function (id) {
      var o = origEdges[id];
      return es.has(id)
        ? {id: id, color: {color: o.color, opacity: 1}, width: o.width * 2, font: o.font}
        : {id: id, color: {color: o.color, opacity: 0.07}, width: o.width,
           font: {color: "rgba(0,0,0,0)", strokeWidth: 0}};
    }));
    active = true;
  }
  function reset() {
    if (!active) { return; }
    nodes.update(Object.keys(origNodes).map(function (id) {
      return {id: id, color: origNodes[id].color, font: origNodes[id].font};
    }));
    edges.update(Object.keys(origEdges).map(function (id) {
      var o = origEdges[id];
      return {id: id, color: {color: o.color, opacity: 1}, width: o.width, font: o.font};
    }));
    active = false;
  }
  network.on("hoverNode", function (p) {
    var es = [];
    network.getConnectedEdges(p.node).forEach(function (id) { es = es.concat(groupOf(id)); });
    highlight(es, [p.node]);
  });
  network.on("hoverEdge", function (p) { highlight(groupOf(p.edge), []); });
  network.on("blurNode", reset);
  network.on("blurEdge", reset);
  function freeze() { network.setOptions({physics: {enabled: false}}); }
  network.once("stabilizationIterationsDone", freeze);
  network.once("stabilized", freeze);
})();
</script>
"""


def _fmt_number(value: float) -> str:
    """Format a capacity value compactly."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    return f"{value:,.1f}"


def _members_text(members: list[str]) -> str:
    """List member names, truncated to :data:`MAX_TOOLTIP_MEMBERS`."""
    shown = members[:MAX_TOOLTIP_MEMBERS]
    lines = [f"  • {m}" for m in shown]
    if len(members) > len(shown):
        lines.append(f"  … and {len(members) - len(shown)} more")
    return "\n".join(lines)


def _eff_name(port: int) -> str:
    """Name of the efficiency attribute of a link port."""
    return "η" if port == 1 else f"η{port}"


def efficiency_text(edge: Edge) -> str:
    """Return the signed efficiency label of a link edge, e.g. ``η2=-0.25``.

    Parameters
    ----------
    edge : Edge
        A link edge.

    Returns
    -------
    str
        Empty string when no efficiency is known; a range ``min…max`` when the
        aggregated members differ.
    """
    if not edge.efficiencies:
        return ""
    lo, hi = min(edge.efficiencies), max(edge.efficiencies)
    if math.isclose(lo, hi, rel_tol=1e-6, abs_tol=1e-9):
        return f"{_eff_name(edge.port)}={lo:+.3g}"
    return f"{_eff_name(edge.port)}={lo:+.3g}…{hi:+.3g}"


def _edge_label(edge: Edge, aggregated: bool) -> str:
    """Visible label of an edge."""
    if edge.kind == "Attachment":
        return ""
    name = edge.carrier
    if aggregated or len(edge.members) > 1:
        name += f" (n={len(edge.members)})"
    eff = efficiency_text(edge)
    return f"{name}\n{eff}" if eff else name


def _edge_title(edge: Edge, nodes: dict[str, Node]) -> str:
    """Tooltip text of an edge."""
    if edge.kind == "Attachment":
        return _node_title(nodes[edge.target])
    lines = [
        f"{edge.kind}: {edge.carrier}",
        f"port: bus0 ({nodes[edge.source].label}) → bus{edge.port} "
        f"({nodes[edge.target].label})",
    ]
    eff = efficiency_text(edge)
    if eff:
        lines.append(f"efficiency: {eff}")
    lines.append(f"capacity (sum): {_fmt_number(edge.capacity)}")
    lines.append(f"components: {len(edge.members)}")
    lines.append(_members_text(edge.members))
    return "\n".join(lines)


def _node_title(node: Node) -> str:
    """Tooltip text of a node."""
    if node.kind == "Bus":
        head = f"Bus carrier: {node.carrier}"
        if node.is_start:
            head += "  (selected carrier)"
        return "\n".join(
            [head, f"buses: {len(node.members)}", _members_text(node.members)]
        )
    return "\n".join(
        [
            f"{node.kind}: {node.carrier}",
            f"capacity (sum): {_fmt_number(node.capacity)}",
            f"components: {len(node.members)}",
            _members_text(node.members),
        ]
    )


def _smooth_settings(edges: list[Edge]) -> list[dict]:
    """Curve parallel edges and size self-loops so they do not overlap."""
    pair_count: dict[tuple, int] = defaultdict(int)
    for e in edges:
        pair_count[tuple(sorted((e.source, e.target)))] += 1
    pair_index: dict[tuple, int] = defaultdict(int)
    settings = []
    for e in edges:
        key = tuple(sorted((e.source, e.target)))
        k = pair_index[key]
        pair_index[key] += 1
        extra: dict = {}
        if e.source == e.target:
            extra["selfReference"] = {"size": 25 + 12 * k, "angle": 0.6 * k}
        elif pair_count[key] > 1:
            # forward/backward direction curve to the same side visually
            clockwise = (k % 2 == 0) == (e.source < e.target)
            extra["smooth"] = {
                "enabled": True,
                "type": "curvedCW" if clockwise else "curvedCCW",
                "roundness": 0.12 + 0.12 * (k // 2),
            }
        settings.append(extra)
    return settings


def build_network(graph: TopologyGraph) -> Network:
    """Convert a topology graph into a pyvis network.

    Parameters
    ----------
    graph : TopologyGraph
        The graph to convert.

    Returns
    -------
    pyvis.network.Network
    """
    net = Network(
        height="85vh",
        width="100%",
        directed=True,
        cdn_resources="in_line",
    )
    for node in graph.nodes.values():
        color = carrier_color(node.carrier, graph.colors)
        is_bus = node.kind == "Bus"
        net.add_node(
            node.id,
            label=node.label,
            title=_node_title(node),
            shape=_NODE_SHAPES.get(node.kind, "dot"),
            color=color,
            size=(34 if node.is_start else 22) if is_bus else 11,
            borderWidth=4 if node.is_start else 1,
            font={"color": "#222222", "size": 16 if is_bus else 11},
        )
    for i, (edge, extra) in enumerate(zip(graph.edges, _smooth_settings(graph.edges))):
        attachment = edge.kind == "Attachment"
        net.add_edge(
            edge.source,
            edge.target,
            id=f"e{i}",
            linkgroup=edge.group,
            label=_edge_label(edge, graph.aggregated),
            title=_edge_title(edge, graph.nodes),
            color=(
                "#9a9a9a" if attachment else carrier_color(edge.carrier, graph.colors)
            ),
            width=1 if attachment else (3 if edge.kind != "Link" else 2),
            dashes=attachment,
            arrows="" if attachment else "to",
            font={"color": "#333333", "size": 11, "strokeWidth": 4},
            **extra,
        )
    net.options = _OPTIONS
    return net


def _header(graph: TopologyGraph) -> str:
    """HTML header describing the plot."""
    view = (
        "aggregated by carrier (all buses of a carrier merged into one node)"
        if graph.aggregated
        else f"detailed for region '{graph.region}'"
    )
    n_bus = sum(1 for n in graph.nodes.values() if n.kind == "Bus")
    n_branch = sum(1 for e in graph.edges if e.kind != "Attachment")
    title = f"Topology around carrier '{graph.carrier}'"
    if graph.region is not None:
        title += f" in region '{graph.region}'"
    return (
        '<div id="topology-header">'
        f"<h2>{html.escape(title)}</h2>"
        f"<p>View: {html.escape(view)} · depth {graph.depth} · "
        f"{n_bus} bus nodes · {n_branch} branch lines</p>"
        "<p>● bus &nbsp; ▲ generator &nbsp; ▼ load &nbsp; ■ store &nbsp; "
        "◆ storage unit &nbsp; · Lines of one multilink share colour and label; "
        "arrows point bus0 → busN, labels show the signed efficiency. "
        "Hover a node or line to highlight its connections.</p>"
        "</div>"
    )


def topology_html(graph: TopologyGraph) -> str:
    """Return the complete HTML document for *graph*.

    Parameters
    ----------
    graph : TopologyGraph
        The graph to render.

    Returns
    -------
    str
        Self-contained HTML (vis-network is inlined).
    """
    content = build_network(graph).generate_html(notebook=False)
    content = content.replace("</head>", _CSS + "</head>", 1)
    content = re.sub(r"<body>", "<body>" + _header(graph), content, count=1)
    idx = content.rfind("</body>")
    return content[:idx] + _HIGHLIGHT_JS + content[idx:]


def output_filename(carrier: str, region: str | None = None) -> str:
    """Return a filesystem-safe file name ``<carrier>[_<region>].html``.

    Parameters
    ----------
    carrier : str
        Carrier name.
    region : str or None, optional
        Region name.

    Returns
    -------
    str
    """
    stem = carrier if region is None else f"{carrier}_{region}"
    return re.sub(r"[^\w.\-]+", "_", stem).strip("_") + ".html"


def write_topology_html(graph: TopologyGraph, path: str | Path) -> Path:
    """Write the interactive HTML for *graph* to *path*.

    Parameters
    ----------
    graph : TopologyGraph
        The graph to render.
    path : str or pathlib.Path
        Destination file.

    Returns
    -------
    pathlib.Path
        The written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(topology_html(graph), encoding="utf-8")
    return path


__all__ = [
    "build_network",
    "efficiency_text",
    "output_filename",
    "topology_html",
    "write_topology_html",
]
