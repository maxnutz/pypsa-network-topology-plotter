"""
graph – select the part of a pypsa network around a carrier and build a
plot-independent topology graph from it.

Two views are produced:

* **aggregated** (no region given): all buses of the same bus carrier are
  merged into one node, branches are grouped by (component, carrier, port).
* **detailed** (region given): every bus and every component is its own node
  or edge.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pypsa

from .utils import InputError

#: One-port components attached to a single bus: name -> network attribute.
ONE_PORT_COMPONENTS: dict[str, str] = {
    "Generator": "generators",
    "Load": "loads",
    "Store": "stores",
    "StorageUnit": "storage_units",
}

#: Branch components connecting two or more buses: name -> network attribute.
BRANCH_COMPONENTS: dict[str, str] = {
    "Link": "links",
    "Line": "lines",
    "Transformer": "transformers",
}

#: Capacity attribute reported in tooltips, per component (optimised first).
_CAPACITY_ATTRS: dict[str, tuple[str, ...]] = {
    "Generator": ("p_nom_opt", "p_nom"),
    "StorageUnit": ("p_nom_opt", "p_nom"),
    "Store": ("e_nom_opt", "e_nom"),
    "Link": ("p_nom_opt", "p_nom"),
    "Line": ("s_nom_opt", "s_nom"),
    "Transformer": ("s_nom_opt", "s_nom"),
}

_FALLBACK_PALETTE: tuple[str, ...] = (
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#1f77b4",
    "#d62728",
)

_PORT_COLUMNS = ["component", "name", "carrier", "port", "bus0", "bus", "efficiency"]


@dataclass
class Node:
    """A node of the topology graph (a bus or a one-port component).

    Attributes
    ----------
    id : str
        Unique node id.
    label : str
        Text shown on the node.
    kind : str
        ``"Bus"`` or a one-port component name (``"Generator"``, …).
    carrier : str
        Carrier of the bus / component.
    members : list of str
        Names of the pypsa components behind this node.
    capacity : float
        Summed capacity of the members (NaN when not applicable).
    is_start : bool
        Whether the node holds the requested carrier bus(es).
    """

    id: str
    label: str
    kind: str
    carrier: str
    members: list[str] = field(default_factory=list)
    capacity: float = np.nan
    is_start: bool = False


@dataclass
class Edge:
    """A directed edge of the topology graph.

    One edge represents one port of a branch (``bus0 -> bus<port>``) or the
    attachment of a one-port component to its bus.

    Attributes
    ----------
    source, target : str
        Node ids.
    kind : str
        ``"Link"``, ``"Line"``, ``"Transformer"`` or ``"Attachment"``.
    carrier : str
        Carrier of the branch / component.
    group : str
        Edges sharing a group belong to the same (multi)link (detailed view)
        or the same link carrier (aggregated view).
    port : int
        Port number of the branch (1 for ``bus1``, …); 0 for attachments.
    efficiencies : list of float
        Static efficiencies of the members for this port (links only).
    members : list of str
        Names of the pypsa components behind this edge.
    capacity : float
        Summed capacity of the members.
    """

    source: str
    target: str
    kind: str
    carrier: str
    group: str
    port: int
    efficiencies: list[float] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    capacity: float = np.nan


@dataclass
class TopologyGraph:
    """Plot-independent topology graph around one carrier."""

    carrier: str
    region: str | None
    depth: int
    aggregated: bool
    nodes: dict[str, Node]
    edges: list[Edge]
    colors: dict[str, str]


def carrier_color(carrier: str, colors: dict[str, str]) -> str:
    """Return the colour of *carrier* from *colors* or a stable fallback.

    Parameters
    ----------
    carrier : str
        Carrier name.
    colors : dict of {str: str}
        Known carrier colours (e.g. from ``n.carriers.color``).

    Returns
    -------
    str
        A colour string usable in HTML.
    """
    color = colors.get(carrier)
    if isinstance(color, str) and color.strip():
        return color
    digest = int(hashlib.md5(carrier.encode("utf8")).hexdigest(), 16)
    return _FALLBACK_PALETTE[digest % len(_FALLBACK_PALETTE)]


def _capacity(component: str, df: pd.DataFrame) -> pd.Series:
    """Capacity per row of *df*, preferring optimised values when present."""
    for attr in _CAPACITY_ATTRS.get(component, ()):
        if attr in df.columns:
            values = pd.to_numeric(df[attr], errors="coerce")
            if attr.endswith("_opt") and not (values > 0).any():
                continue
            return values
    return pd.Series(np.nan, index=df.index)


def branch_ports(n: pypsa.Network) -> pd.DataFrame:
    """Return all branch ports of *n* in long format.

    Each row is one ``bus0 -> bus<port>`` connection of a link, line or
    transformer. Empty ports of multi-port links and ports referring to buses
    that do not exist in ``n.buses`` are dropped.

    Parameters
    ----------
    n : pypsa.Network
        The network.

    Returns
    -------
    pandas.DataFrame
        Columns ``component, name, carrier, port, bus0, bus, efficiency,
        capacity``.
    """
    frames = []
    for component, attr in BRANCH_COMPONENTS.items():
        df = getattr(n, attr)
        if df.empty:
            continue
        carrier = (
            df["carrier"].fillna("").astype(str).replace("", component)
            if "carrier" in df.columns
            else pd.Series(component, index=df.index)
        )
        capacity = _capacity(component, df)
        ports = sorted(
            int(c[3:]) for c in df.columns if re.fullmatch(r"bus\d+", c) and c != "bus0"
        )
        for port in ports:
            eff_col = "efficiency" if port == 1 else f"efficiency{port}"
            efficiency = (
                pd.to_numeric(df[eff_col], errors="coerce")
                if component == "Link" and eff_col in df.columns
                else pd.Series(np.nan, index=df.index)
            )
            frame = pd.DataFrame(
                {
                    "component": component,
                    "name": df.index.astype(str),
                    "carrier": carrier.to_numpy(),
                    "port": port,
                    "bus0": df["bus0"].fillna("").astype(str).to_numpy(),
                    "bus": df[f"bus{port}"].fillna("").astype(str).to_numpy(),
                    "efficiency": efficiency.to_numpy(),
                    "capacity": capacity.to_numpy(),
                }
            )
            # drop empty ports and ports pointing to buses missing in n.buses
            valid = frame["bus"].isin(n.buses.index) & frame["bus0"].isin(n.buses.index)
            frames.append(frame[valid])
    if not frames:
        return pd.DataFrame(columns=_PORT_COLUMNS + ["capacity"])
    return pd.concat(frames, ignore_index=True)


def _branch_signatures(ports: pd.DataFrame) -> pd.Series:
    """Topology signature of the branch behind each port row.

    Two branches share a signature when they have the same component,
    carrier and ``bus0`` and identical ``(port, bus, efficiency)`` for every
    port, e.g. build-year vintages of the same link. Efficiencies are compared
    after rounding to 6 decimals.

    Parameters
    ----------
    ports : pandas.DataFrame
        Port table as returned by :func:`branch_ports`.

    Returns
    -------
    pandas.Series
        One signature string per row of *ports* (aligned to its index).
    """
    # lines/transformers have no efficiency; pandas>=3 keeps NaN through astype(str)
    eff = ports["efficiency"].round(6).astype(str).fillna("nan")
    part = ports["port"].astype(str) + ":" + ports["bus"] + ":" + eff
    per_branch = (
        part.groupby([ports["component"], ports["name"]], sort=False)
        .agg(lambda s: "|".join(sorted(s)))
        .rename("ports")
    )
    keys = pd.MultiIndex.from_frame(ports[["component", "name"]])
    return pd.Series(
        ports["component"]
        + "|"
        + ports["carrier"]
        + "|"
        + ports["bus0"]
        + "|"
        + per_branch.reindex(keys).to_numpy(),
        index=ports.index,
    )


class CarrierTopology:
    """Select the sub-network around a carrier.

    Parameters
    ----------
    n : pypsa.Network
        The network to evaluate.
    carrier : str
        Bus carrier to start from (exact match against ``n.buses.carrier``).
    region : str or None, optional
        Restrict the start buses to a region. If any ``bus.location`` equals
        *region*, buses are matched by location; otherwise by substring of
        the bus name. Without a region the graph is aggregated by carrier.
    depth : int, optional
        Number of bus hops expanded from the start buses over links, lines
        and transformers. Defaults to 1.

    Attributes
    ----------
    start_buses : pandas.Index
        Buses of *carrier* (within *region*).
    buses : pandas.Index
        All buses included after the expansion.
    ports : pandas.DataFrame
        Selected branch ports (see :func:`branch_ports`).
    one_ports : pandas.DataFrame
        One-port components attached to included buses, columns
        ``component, name, carrier, bus, capacity``.

    Raises
    ------
    InputError
        When the carrier or the region matches no bus, or depth < 0.
    """

    def __init__(
        self,
        n: pypsa.Network,
        carrier: str,
        region: str | None = None,
        depth: int = 1,
    ) -> None:
        if depth < 0:
            raise InputError(f"depth must be >= 0, got {depth}.")
        self.n = n
        self.carrier = carrier
        self.region = region
        self.depth = depth
        self.start_buses = self._find_start_buses()
        self.ports, self.buses = self._expand(branch_ports(n))
        self.one_ports = self._attached_one_ports()

    def __repr__(self) -> str:
        return (
            f"CarrierTopology(carrier={self.carrier!r}, region={self.region!r}, "
            f"depth={self.depth}, start_buses={len(self.start_buses)}, "
            f"buses={len(self.buses)}, ports={len(self.ports)})"
        )

    @property
    def aggregated(self) -> bool:
        """Whether the graph is aggregated by carrier (no region given)."""
        return self.region is None

    def _find_start_buses(self) -> pd.Index:
        """Return the buses of the carrier, optionally within the region."""
        buses = self.n.buses
        bus_carriers = buses["carrier"].astype(str)
        mask = bus_carriers == self.carrier
        if not mask.any():
            suggestions = difflib.get_close_matches(
                self.carrier, sorted(bus_carriers.unique()), n=5, cutoff=0.4
            )
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            raise InputError(f"No bus with carrier '{self.carrier}' found.{hint}")
        if self.region is not None:
            if "location" in buses.columns and (buses["location"] == self.region).any():
                region_mask = buses["location"] == self.region
            else:
                region_mask = buses.index.astype(str).str.contains(
                    self.region, regex=False
                )
            mask &= region_mask
            if not mask.any():
                raise InputError(
                    f"No bus with carrier '{self.carrier}' found in region "
                    f"'{self.region}' (checked bus.location and bus names)."
                )
        return buses.index[mask]

    def _expand(self, ports: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
        """Expand from the start buses by ``depth`` bus hops.

        A branch is selected as a whole (all of its ports) as soon as any of
        its buses is included.
        """
        included = set(self.start_buses)
        selected = pd.Series(False, index=ports.index)
        branch_key = pd.MultiIndex.from_frame(ports[["component", "name"]])
        for _ in range(self.depth):
            touching = ports["bus0"].isin(included) | ports["bus"].isin(included)
            whole = branch_key.isin(branch_key[touching.to_numpy()])
            new_selected = selected | whole
            if new_selected.equals(selected):
                break
            selected = new_selected
            chosen = ports[selected]
            included |= set(chosen["bus0"]) | set(chosen["bus"])
        bus_order = [b for b in self.n.buses.index if b in included]
        return ports[selected].reset_index(drop=True), pd.Index(bus_order)

    def _attached_one_ports(self) -> pd.DataFrame:
        """Return generators, loads, stores and storage units on included buses."""
        frames = []
        for component, attr in ONE_PORT_COMPONENTS.items():
            df = getattr(self.n, attr)
            if df.empty:
                continue
            df = df[df["bus"].isin(self.buses)]
            if df.empty:
                continue
            carrier = (
                df["carrier"].fillna("").astype(str).replace("", component)
                if "carrier" in df.columns
                else pd.Series(component, index=df.index)
            )
            frames.append(
                pd.DataFrame(
                    {
                        "component": component,
                        "name": df.index.astype(str),
                        "carrier": carrier.to_numpy(),
                        "bus": df["bus"].astype(str).to_numpy(),
                        "capacity": _capacity(component, df).to_numpy(),
                    }
                )
            )
        if not frames:
            return pd.DataFrame(
                columns=["component", "name", "carrier", "bus", "capacity"]
            )
        return pd.concat(frames, ignore_index=True)

    def build_graph(self) -> TopologyGraph:
        """Build the topology graph (aggregated or detailed).

        Returns
        -------
        TopologyGraph
        """
        n = self.n
        bus_carrier = n.buses["carrier"].astype(str)
        start = set(self.start_buses)
        aggregated = self.aggregated

        def bus_key(bus: str) -> str:
            return f"bus|{bus_carrier.get(bus, '?')}" if aggregated else f"bus|{bus}"

        nodes: dict[str, Node] = {}
        for bus in self.buses:
            key = bus_key(bus)
            if key not in nodes:
                nodes[key] = Node(
                    id=key,
                    label=bus_carrier.get(bus, "?") if aggregated else bus,
                    kind="Bus",
                    carrier=bus_carrier.get(bus, "?"),
                )
            nodes[key].members.append(bus)
            nodes[key].is_start |= bus in start

        edges: list[Edge] = []
        ports = self.ports.assign(
            source=self.ports["bus0"].map(bus_key),
            target=self.ports["bus"].map(bus_key),
        )
        if aggregated:
            keys = ["component", "carrier", "port", "source", "target"]
            for (component, carrier, port, source, target), grp in ports.groupby(
                keys, sort=True
            ):
                edges.append(
                    Edge(
                        source=source,
                        target=target,
                        kind=component,
                        carrier=carrier,
                        group=f"{component}|{carrier}",
                        port=int(port),
                        efficiencies=grp["efficiency"].dropna().tolist(),
                        members=grp["name"].tolist(),
                        capacity=grp["capacity"].sum(min_count=1),
                    )
                )
        else:
            ports = ports.assign(signature=_branch_signatures(ports))
            keys = ["component", "carrier", "signature", "port", "source", "target"]
            for (component, carrier, _, port, source, target), grp in ports.groupby(
                keys, sort=False
            ):
                names = grp["name"].tolist()
                efficiency = grp["efficiency"].iloc[0]
                edges.append(
                    Edge(
                        source=source,
                        target=target,
                        kind=component,
                        carrier=carrier,
                        group=f"{component}|{names[0]}",
                        port=int(port),
                        efficiencies=[] if pd.isna(efficiency) else [efficiency],
                        members=names,
                        capacity=grp["capacity"].sum(min_count=1),
                    )
                )

        one_ports = self.one_ports.assign(bus_key=self.one_ports["bus"].map(bus_key))
        if aggregated:
            groups = one_ports.groupby(["component", "carrier", "bus_key"], sort=True)
            items = [
                (
                    f"{c}|{car}|{bk}",
                    car,
                    c,
                    car,
                    bk,
                    grp["name"].tolist(),
                    grp["capacity"].sum(min_count=1),
                )
                for (c, car, bk), grp in groups
            ]
        else:
            items = [
                (
                    f"{r.component}|{r.name}",
                    r.name,
                    r.component,
                    r.carrier,
                    r.bus_key,
                    [r.name],
                    r.capacity,
                )
                for r in one_ports.itertuples(index=False)
            ]
        for node_id, label, component, carrier, bk, members, capacity in items:
            nodes[node_id] = Node(
                id=node_id,
                label=label,
                kind=component,
                carrier=carrier,
                members=members,
                capacity=capacity,
            )
            edges.append(
                Edge(
                    source=bk,
                    target=node_id,
                    kind="Attachment",
                    carrier=carrier,
                    group=f"attach|{node_id}",
                    port=0,
                    members=members,
                    capacity=capacity,
                )
            )

        colors = (
            n.carriers["color"].dropna().astype(str).to_dict()
            if "color" in n.carriers.columns
            else {}
        )
        return TopologyGraph(
            carrier=self.carrier,
            region=self.region,
            depth=self.depth,
            aggregated=aggregated,
            nodes=nodes,
            edges=edges,
            colors=colors,
        )
