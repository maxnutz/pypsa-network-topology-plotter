#!/usr/bin/env python3

import os
from io import BytesIO

import numpy as np
import pandas as pd
import pypsa
from PIL import UnidentifiedImageError


class InputError(Exception):
    """Raised when no component with the given carrier is found in the network."""

    pass


class CarriersNetwork:
    # ------------------------------------------------------------------
    # Bus-count limit constants
    # ------------------------------------------------------------------
    _BUS_LIMIT_TRIGGER: int = 7   # trim when primary bus count exceeds this
    _BUS_LIMIT_TARGET: int = 5    # how many primary buses to keep after trimming
    _BUS_HARD_CAP: int = 12       # absolute maximum primary bus count

    def __init__(
        self,
        carrier: str,
        n: pypsa.Network,
        eval_one_node: bool = False,
        search_therm: bool | str = None,
        bus_pattern: str | None = None,
    ):
        """
        Initialises the CarriersNetwork class.

        Parameters
        ----------
        carrier : str
            The name of the carrier for which the network should be evaluated.
        n : pypsa.Network
            The network object to be evaluated.
        eval_one_node : bool, optional
            Whether to reduce the network to one node. Defaults to False.
        search_therm : bool | str, optional
            The search term to be used when reducing the network to one node.
            Defaults to None.
        bus_pattern : str or None, optional
            When provided, only buses whose index contains *bus_pattern* (and
            all components connected to those buses) are kept.  This allows
            restricting the topology plot to a sub-set of the carrier network,
            for example ``bus_pattern="AT0"`` to focus on a specific region.
            Defaults to None (no filtering).

        Attributes
        ----------
        carrier : str
        n : pypsa.Network
        initial_component_type : str or None
            The name of the component type in which ``carrier`` was first found
            (one of ``'bus'``, ``'link'``, ``'line'``, ``'store'``,
            ``'storage_unit'``, ``'generator'``, ``'load'``).  Set during
            initialisation by :meth:`_find_buses_by_carrier`.
        initial_components : pandas.DataFrame or None
            The rows of the first component type where ``carrier`` was found.
        generators : pandas.DataFrame
        buses : pandas.DataFrame
        links : pandas.DataFrame
        lines : pandas.DataFrame
        stores : pandas.DataFrame
        storage_units : pandas.DataFrame
        loads : pandas.DataFrame
        processes : numpy.ndarray
        """
        self.carrier = carrier
        self.n = n
        self.initial_component_type = None
        self.initial_components = None
        self.buses = self._find_buses_by_carrier()
        if self.buses.empty:
            raise InputError(
                f"No component with carrier '{self.carrier}' found in the network. "
                "Searched buses, links, lines, stores, storage_units, generators, "
                "and loads."
            )
        self.generators = self.get_generators()
        self.links = self.get_links()
        self.lines = self.get_lines()
        self.stores = self.get_stores()
        self.storage_units = self.get_storage_units()
        self.loads = self.get_load()
        self.processes = self.get_all_processes()
        if eval_one_node:
            self.reduce_to_one_node(search_therm)
        if bus_pattern is not None:
            self.filter_by_bus_pattern(bus_pattern)
        else:
            # Even without a bus_pattern, enforce the hard cap so that large
            # networks (e.g. a carrier present in every country bus) don't
            # produce an unreadable diagram.
            self._apply_bus_limit()

    def _find_buses_by_carrier(self) -> pd.DataFrame:
        """
        Find buses connected to ``self.carrier`` by searching all component
        types in order: buses, links, lines, stores, storage_units, generators,
        loads.

        Sets ``self.initial_component_type`` to the name of the first
        component type where the carrier was found, and
        ``self.initial_components`` to the matching rows of that component.

        Returns
        -------
        pd.DataFrame
            Buses of or connected to the found components.  Returns an empty
            DataFrame when the carrier is not found in any component.
        """
        # 1. Buses
        buses = self.get_buses()
        if not buses.empty:
            self.initial_component_type = "bus"
            self.initial_components = buses
            return buses

        # 2. Links
        links_with_carrier = self.n.links[
            self.n.links.carrier.str.contains(self.carrier)
        ]
        if not links_with_carrier.empty:
            self.initial_component_type = "link"
            self.initial_components = links_with_carrier
            bus_names = set(links_with_carrier.bus0.values) | set(
                links_with_carrier.bus1.values
            )
            for col in self._extra_bus_cols(links_with_carrier):
                bus_names |= set(links_with_carrier[col].values)
            bus_names.discard("")
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        # 3. Lines
        lines_with_carrier = self.n.lines[
            self.n.lines.carrier.str.contains(self.carrier)
        ]
        if not lines_with_carrier.empty:
            self.initial_component_type = "line"
            self.initial_components = lines_with_carrier
            bus_names = set(lines_with_carrier.bus0.values) | set(
                lines_with_carrier.bus1.values
            )
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        # 4. Stores
        stores_with_carrier = self.n.stores[
            self.n.stores.carrier.str.contains(self.carrier)
        ]
        if not stores_with_carrier.empty:
            self.initial_component_type = "store"
            self.initial_components = stores_with_carrier
            bus_names = set(stores_with_carrier.bus.values)
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        # 5. Storage units
        storage_units_with_carrier = self.n.storage_units[
            self.n.storage_units.carrier.str.contains(self.carrier)
        ]
        if not storage_units_with_carrier.empty:
            self.initial_component_type = "storage_unit"
            self.initial_components = storage_units_with_carrier
            bus_names = set(storage_units_with_carrier.bus.values)
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        # 6. Generators
        generators_with_carrier = self.n.generators[
            self.n.generators.carrier.str.contains(self.carrier)
        ]
        if not generators_with_carrier.empty:
            self.initial_component_type = "generator"
            self.initial_components = generators_with_carrier
            bus_names = set(generators_with_carrier.bus.values)
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        # 7. Loads
        loads_with_carrier = self.n.loads[
            self.n.loads.carrier.str.contains(self.carrier)
        ]
        if not loads_with_carrier.empty:
            self.initial_component_type = "load"
            self.initial_components = loads_with_carrier
            bus_names = set(loads_with_carrier.bus.values)
            return self.n.buses[self.n.buses.index.isin(bus_names)]

        return pd.DataFrame()

    def reduce_to_one_node(self, search_therm: str | None) -> None:
        """
        Reduces the network of the current carrier to one node.

        Parameters
        ----------
        search_therm : str or None
            Name of the node to search for (e.g. 'AT0'). The carrier name is
            appended to build the bus search string.  When *None* the first
            bus of the carrier is used.
        """
        self.get_search_therms(search_therm)
        self.generators = self.generators[
            self.generators.bus.str.contains(self.search_node)
        ]
        self.buses = self.buses[self.buses.index.str.contains(self.search_node)]
        link_frames = [
            self.links[self.links.bus0.str.contains(self.search_string)],
            self.links[self.links.bus1.str.contains(self.search_string)],
        ]
        for col in self._extra_bus_cols(self.links):
            link_frames.append(
                self.links[self.links[col].str.contains(self.search_string)]
            )
        self.links = pd.concat(link_frames).drop_duplicates()
        self.lines = pd.concat(
            [
                self.lines[self.lines.bus0.str.contains(self.search_string)],
                self.lines[self.lines.bus1.str.contains(self.search_string)],
            ]
        )
        self.stores = self.stores[self.stores.bus.str.contains(self.search_node)]
        self.storage_units = self.storage_units[
            self.storage_units.bus.str.contains(self.search_node)
        ]
        self.loads = self.loads[self.loads.bus.str.contains(self.search_node)]
        self.processes = self.get_all_processes()

    def get_search_therms(self, search_therm: str | None) -> None:
        """
        Build the search strings used to filter components to one node.

        Parameters
        ----------
        search_therm : str or None
            Node identifier.  When *None* the first bus of the carrier is used.
        """
        if search_therm:
            self.search_node = search_therm + " " + self.carrier
            self.search_string = search_therm
        else:
            self.search_node = self.buses.index.unique()[0].replace(
                " " + self.carrier, ""
            )
            self.search_string = self.buses.index.unique()[0]

    def filter_by_bus_pattern(self, bus_pattern: str) -> None:
        """
        Restrict the network to buses whose index contains *bus_pattern*.

        All components (generators, loads, stores, storage units) that are
        attached to a matching bus are kept.  Links and lines are kept when
        at least one of their bus endpoints matches the pattern.

        After filtering, :meth:`_apply_bus_limit` is called automatically so
        that an unexpectedly large result set is trimmed to a manageable size.

        Parameters
        ----------
        bus_pattern : str
            Substring to search for in bus indices (case-sensitive).
        """
        self.buses = self.buses[self.buses.index.str.contains(bus_pattern)]
        if self.buses.empty:
            raise ValueError(
                f"No buses matching pattern '{bus_pattern}' found for carrier "
                + self.carrier
            )
        self._refilter_by_buses()
        self._apply_bus_limit()

    def _refilter_by_buses(self) -> None:
        """
        Refilter all component DataFrames so they are consistent with
        ``self.buses``.

        Called internally after any operation that changes ``self.buses``
        (e.g. :meth:`filter_by_bus_pattern` and :meth:`_apply_bus_limit`).
        """
        self.generators = self.generators[
            self.generators.bus.isin(self.buses.index)
        ]
        self.loads = self.loads[self.loads.bus.isin(self.buses.index)]
        self.stores = self.stores[self.stores.bus.isin(self.buses.index)]
        self.storage_units = self.storage_units[
            self.storage_units.bus.isin(self.buses.index)
        ]
        link_frames = [
            self.links[self.links.bus0.isin(self.buses.index)],
            self.links[self.links.bus1.isin(self.buses.index)],
        ]
        for col in self._extra_bus_cols(self.links):
            link_frames.append(self.links[self.links[col].isin(self.buses.index)])
        self.links = pd.concat(link_frames).drop_duplicates()
        self.lines = pd.concat(
            [
                self.lines[self.lines.bus0.isin(self.buses.index)],
                self.lines[self.lines.bus1.isin(self.buses.index)],
            ]
        ).drop_duplicates()
        self.processes = self.get_all_processes()

    def _apply_bus_limit(self) -> None:
        """
        Trim the primary bus list when it is too large and refilter components.

        When the number of primary carrier buses (:attr:`buses`) exceeds
        :attr:`_BUS_LIMIT_TRIGGER` (default 7), the list is truncated to the
        first :attr:`_BUS_LIMIT_TARGET` (default 5) buses.  An absolute hard
        cap of :attr:`_BUS_HARD_CAP` (default 12) is always enforced on both
        primary buses and the total buses displayed in the diagram.

        After trimming all component DataFrames are updated via
        :meth:`_refilter_by_buses` to stay consistent.
        """
        n = len(self.buses)
        if n > self._BUS_HARD_CAP:
            self.buses = self.buses.iloc[: self._BUS_HARD_CAP]
            self._refilter_by_buses()
        elif n > self._BUS_LIMIT_TRIGGER:
            self.buses = self.buses.iloc[: self._BUS_LIMIT_TARGET]
            self._refilter_by_buses()

        # Also enforce hard cap on total buses shown in diagram (including secondary buses)
        self._enforce_diagram_bus_cap()

    def _enforce_diagram_bus_cap(self) -> None:
        """
        Enforce hard cap on total buses displayed in the diagram.

        Counts all buses that would appear in the final mermaid diagram
        (primary buses plus secondary buses from links/lines). If the total
        exceeds :attr:`_BUS_HARD_CAP`, keeps primary buses and instead limits
        the links/lines to ensure the diagram stays within limits.
        """
        # Collect all buses that would appear in the diagram
        diagram_buses: set = set(self.buses.index)

        # Add secondary buses from links
        if not self.links.empty:
            diagram_buses.update(self.links.bus0.values)
            diagram_buses.update(self.links.bus1.values)
            for col in self._extra_bus_cols(self.links):
                bus_vals = self.links[col].values
                diagram_buses.update([b for b in bus_vals if b != ""])

        # Add secondary buses from lines
        if not self.lines.empty:
            diagram_buses.update(self.lines.bus0.values)
            diagram_buses.update(self.lines.bus1.values)

        # Remove empty strings
        diagram_buses.discard("")
        total_buses = len(diagram_buses)

        # If total buses exceed hard cap, trim links and lines to reduce diagram size
        if total_buses > self._BUS_HARD_CAP:
            # Strategy: keep only links/lines that connect to the first N primary buses
            # and limit secondary buses to reach the hard cap
            remaining_cap = self._BUS_HARD_CAP - len(self.buses)
            
            if remaining_cap < 0:
                # Primary buses alone exceed cap - this shouldn't happen after _apply_bus_limit
                return
            
            # Keep track of which secondary buses are connected
            secondary_buses: set = set()
            kept_links = []
            kept_lines = []
            
            # First pass: keep links to primary buses, stop when we reach the cap
            if not self.links.empty:
                for idx, row in self.links.iterrows():
                    if len(secondary_buses) >= remaining_cap:
                        break
                    
                    # Count new buses this link would add
                    new_buses = set()
                    if row.bus0 not in self.buses.index:
                        new_buses.add(row.bus0)
                    if row.bus1 not in self.buses.index:
                        new_buses.add(row.bus1)
                    for col in self._extra_bus_cols(self.links):
                        if pd.notna(row[col]) and row[col] != "" and row[col] not in self.buses.index:
                            new_buses.add(row[col])
                    
                    # Only keep this link if it doesn't exceed capacity
                    if len(secondary_buses) + len(new_buses) <= remaining_cap:
                        kept_links.append(idx)
                        secondary_buses.update(new_buses)
            
            # Second pass: keep lines, stop when we reach the cap
            if not self.lines.empty:
                for idx, row in self.lines.iterrows():
                    if len(secondary_buses) >= remaining_cap:
                        break
                    
                    # Count new buses this line would add
                    new_buses = set()
                    if row.bus0 not in self.buses.index:
                        new_buses.add(row.bus0)
                    if row.bus1 not in self.buses.index:
                        new_buses.add(row.bus1)
                    
                    # Only keep this line if it doesn't exceed capacity
                    if len(secondary_buses) + len(new_buses) <= remaining_cap:
                        kept_lines.append(idx)
                        secondary_buses.update(new_buses)
            
            # Update links and lines to only kept entries
            if kept_links:
                self.links = self.links.loc[kept_links]
            else:
                self.links = pd.DataFrame(columns=self.links.columns)
            
            if kept_lines:
                self.lines = self.lines.loc[kept_lines]
            else:
                self.lines = pd.DataFrame(columns=self.lines.columns)
            
            # Rebuild processes since links/lines have changed
            self.processes = self.get_all_processes()

    def get_generators(self) -> pd.DataFrame:
        """
        Return generators for this carrier's network.

        When the carrier was found on a bus (``initial_component_type == 'bus'``)
        generators are filtered by carrier name, matching the existing
        behaviour.  For all other entry points (link, line, store,
        storage_unit, generator, load) every generator whose bus is one of the
        carrier buses is returned so that the full topology around those buses
        is shown.
        """
        if self.initial_component_type == "bus":
            return self.n.generators[
                self.n.generators.carrier.str.contains(self.carrier)
            ]
        return self.n.generators[self.n.generators.bus.isin(self.buses.index)]

    def get_buses(self) -> pd.DataFrame:
        """
        Return buses of this carrier.

        Notes
        -----
        Prints a warning when generators are attached to buses with a
        different carrier.
        """
        buses_carrier = self.n.buses[self.n.buses.carrier.str.contains(self.carrier)]
        buses_with_no_generator = set(
            self.n.generators[
                self.n.generators.carrier.str.contains(self.carrier)
            ].bus.values
        ) - set(buses_carrier.index.values)
        if buses_with_no_generator and buses_carrier.empty:
            print(
                "There are generators with carrier "
                + self.carrier
                + " attached to a bus with different carrier."
            )
            buses_carrier = self.n.buses[
                self.n.buses.generator.str.contains(self.carrier)
            ]
        return buses_carrier

    @staticmethod
    def _extra_bus_cols(links_df: pd.DataFrame) -> list:
        """
        Return the sorted list of additional bus columns in *links_df*.

        Extra bus columns are those named ``busN`` for N >= 2 that are present
        in *links_df* and contain at least one non-empty value.  The regex
        approach handles non-sequential column numbering correctly.

        Parameters
        ----------
        links_df : pandas.DataFrame
            Links DataFrame (e.g. ``self.links`` or ``self.n.links``).

        Returns
        -------
        list of str
            Column names such as ``['bus2', 'bus3', 'bus4']``, sorted by N.
        """
        import re

        cols = [
            col
            for col in links_df.columns
            if re.match(r"^bus([2-9]|[1-9]\d+)$", col)
            and links_df[col].ne("").any()
        ]
        return sorted(cols, key=lambda c: int(c[3:]))

    def get_links(self) -> pd.DataFrame:
        """Return links connected to the carrier buses."""
        frames = [
            self.n.links[self.n.links.bus0.isin(self.buses.index)],
            self.n.links[self.n.links.bus1.isin(self.buses.index)],
        ]
        for col in self._extra_bus_cols(self.n.links):
            frames.append(self.n.links[self.n.links[col].isin(self.buses.index)])
        return pd.concat(frames).drop_duplicates()

    def get_lines(self) -> pd.DataFrame:
        """Return lines connected to the carrier buses."""
        return pd.concat(
            [
                self.n.lines[self.n.lines.bus0.isin(self.buses.index)],
                self.n.lines[self.n.lines.bus1.isin(self.buses.index)],
            ]
        )

    def get_load(self) -> pd.DataFrame:
        """
        Return loads for this carrier's network.

        When the carrier was found on a bus the existing carrier-based logic
        (with cross-check warning) is used.  For all other entry points every
        load whose bus is one of the carrier buses is returned.

        Notes
        -----
        Prints a warning when loads have a different carrier than their bus
        (bus-entry mode only).
        """
        if self.initial_component_type != "bus":
            return self.n.loads[self.n.loads.bus.isin(self.buses.index)]
        direct_load_of_carrier = self.n.loads[
            self.n.loads.carrier.str.contains(self.carrier)
        ]
        if not direct_load_of_carrier.equals(
            self.n.loads[self.n.loads.bus.isin(self.buses.index)]
        ):
            carriers = self.n.loads[
                self.n.loads.bus.isin(self.buses.index)
            ].carrier.unique()
            print(
                "Loads must have the same carrier as the bus they are attached to but for carrier '"
                + self.carrier
                + "' got different carriers of integrated buses:"
            )
            print("  " + ",".join(carriers))
            return self.n.loads[self.n.loads.bus.isin(self.buses.index)]
        return direct_load_of_carrier

    def get_stores(self) -> pd.DataFrame:
        """
        Return stores for this carrier's network.

        When the carrier was found on a bus the existing carrier-based logic
        (with cross-check warning) is used.  For all other entry points every
        store whose bus is one of the carrier buses is returned.

        Notes
        -----
        Prints a warning when stores have a different carrier than their bus
        (bus-entry mode only).
        """
        if self.initial_component_type != "bus":
            return self.n.stores[self.n.stores.bus.isin(self.buses.index)]
        stores_carrier = self.n.stores[self.n.stores.carrier.str.contains(self.carrier)]
        if not stores_carrier.equals(
            self.n.stores[self.n.stores.bus.isin(self.buses.index)]
        ):
            print(
                "Stores must have the same carrier as the bus they are attached to but got different dataframes."
            )
            return self.n.stores[self.n.stores.bus.isin(self.buses.index)]
        return stores_carrier

    def get_storage_units(self) -> pd.DataFrame:
        """
        Return storage units for this carrier's network.

        When the carrier was found on a bus the existing carrier-based logic
        (with cross-check warning) is used.  For all other entry points every
        storage unit whose bus is one of the carrier buses is returned.

        Notes
        -----
        Prints a warning when storage units have a different carrier than
        their bus (bus-entry mode only).
        """
        if self.initial_component_type != "bus":
            return self.n.storage_units[
                self.n.storage_units.bus.isin(self.buses.index)
            ]
        storage_units_carrier = self.n.storage_units[
            self.n.storage_units.carrier.str.contains(self.carrier)
        ]
        if not storage_units_carrier.equals(
            self.n.storage_units[self.n.storage_units.bus.isin(self.buses.index)]
        ):
            print(
                "Storage units must have the same carrier as the bus they are attached to but got different dataframes."
            )
            return self.n.storage_units[
                self.n.storage_units.bus.isin(self.buses.index)
            ]
        return storage_units_carrier

    def get_all_processes(self) -> np.ndarray:
        """Return unique carrier labels from links and lines."""
        link_processes_of_carrier = self.links.carrier.unique()
        line_processes_of_carrier = self.lines.carrier.unique()
        return np.append(link_processes_of_carrier, line_processes_of_carrier)

    def mermaid_carriers_network(self) -> list:
        """
        Build the Mermaid diagram elements for this carrier sub-network.

        Initial components (those whose carrier matched ``self.carrier`` and
        triggered the bus-search) are rendered with a distinct edge style
        (thick arrows ``==>`` for links/lines) so they stand out in the
        diagram.  Node-type initial components are highlighted via ``style``
        statements added by :meth:`get_mermaid_string`.

        Returns
        -------
        list of list of str
            Nested list of Mermaid node / edge definitions.
        """
        initial_names: set = (
            set(self.initial_components.index.tolist())
            if self.initial_components is not None
            else set()
        )
        initial_type = self.initial_component_type

        mermaid_code = []
        # main buses
        mermaid_code.append(
            [
                "BUS_" + val.replace(" ", "_") + "(((" + val + ")))"
                for val in self.buses.index.values
            ]
        )
        # generators
        mermaid_code.append(
            [
                index.replace(" ", "_")
                + "["
                + index
                + "] === "
                + "BUS_"
                + row.bus.replace(" ", "_")
                for index, row in self.generators.iterrows()
            ]
        )
        # loads
        mermaid_code.append(
            [
                index.replace(" ", "_")
                + "(LOAD "
                + index
                + ") === "
                + "BUS_"
                + row.bus.replace(" ", "_")
                for index, row in self.loads.iterrows()
            ]
        )
        # storage units
        mermaid_code.append(
            [
                index.replace(" ", "_")
                + "(STORAGE_UNIT"
                + index
                + ") === "
                + "BUS_"
                + row.bus.replace(" ", "_")
                for index, row in self.storage_units.iterrows()
            ]
        )
        # stores
        mermaid_code.append(
            [
                index.replace(" ", "_")
                + "(STORE "
                + index
                + ") === "
                + "BUS_"
                + row.bus.replace(" ", "_")
                for index, row in self.stores.iterrows()
            ]
        )
        # buses reachable via links
        list_of_buses = list(self.links.bus0.values) + list(self.links.bus1.values)
        for col in self._extra_bus_cols(self.links):
            list_of_buses += list(self.links[col].values)
        cleaned_list_of_buses = [v for v in list_of_buses if v != ""]
        mermaid_code.append(
            [
                "BUS_" + bus.replace(" ", "_") + "((" + bus + "))"
                for bus in list(set(cleaned_list_of_buses))
            ]
        )
        # link edges – use thick arrow for initial links
        mermaid_code.append(
            [
                "BUS_"
                + row.bus0.replace(" ", "_")
                + (
                    "== " + index + " ==>BUS_"
                    if initial_type == "link" and index in initial_names
                    else "-- " + index + " -->BUS_"
                )
                + row.bus1.replace(" ", "_")
                for index, row in self.links.iterrows()
            ]
        )
        for col in self._extra_bus_cols(self.links):
            mermaid_code.append(
                [
                    "BUS_"
                    + row.bus0.replace(" ", "_")
                    + "-- "
                    + index
                    + f" indirect {col} -->BUS_"
                    + row[col].replace(" ", "_")
                    for index, row in self.links.iterrows()
                    if row[col] != ""
                ]
            )
        # buses and edges from lines – use thick arrow for initial lines
        mermaid_code.append(
            [
                "BUS_" + bus.replace(" ", "_") + "((" + bus + "))"
                for bus in self.lines.bus1.unique()
            ]
        )
        mermaid_code.append(
            [
                "BUS_"
                + row.bus0.replace(" ", "_")
                + (
                    "== " + index + " ==>BUS_"
                    if initial_type == "line" and index in initial_names
                    else "-- " + index + " -->BUS_"
                )
                + row.bus1.replace(" ", "_")
                for index, row in self.lines.iterrows()
            ]
        )
        return mermaid_code

    def get_mermaid_string(self) -> str:
        """
        Return the complete Mermaid flowchart code as a single string.

        All components in the network that match the target carrier are
        highlighted with a pink fill (``#f9d5e5`` / ``#cc0066`` border) via
        Mermaid ``style`` statements appended to the flowchart.

        Returns
        -------
        str
            Mermaid flowchart code ready to be rendered or saved to a file.
        """
        mermaid_code_list = self.mermaid_carriers_network()
        flat = list(
            set([item for sublist in mermaid_code_list for item in sublist])
        )
        code = "flowchart LR;\n  " + "\n  ".join(flat)

        # Highlight all components that have the target carrier.
        # This includes buses, generators, loads, stores, storage units,
        # links, and lines that contain self.carrier.
        highlight = "fill:#f9d5e5,stroke:#cc0066,stroke-width:2px"
        style_lines: list[str] = []

        # Highlight buses with matching carrier
        for bus_name in self.buses.index:
                node_id = "BUS_" + bus_name.replace(" ", "_")
                style_lines.append(f"style {node_id} {highlight}")

        # Highlight generators with matching carrier
        for gen_name in self.generators.index:
                node_id = gen_name.replace(" ", "_")
                style_lines.append(f"style {node_id} {highlight}")

        # Highlight loads with matching carrier
        for load_name in self.loads.index:
                node_id = load_name.replace(" ", "_")
                style_lines.append(f"style {node_id} {highlight}")

        # Highlight stores with matching carrier
        for store_name in self.stores.index:
                node_id = store_name.replace(" ", "_")
                style_lines.append(f"style {node_id} {highlight}")

        # Highlight storage units with matching carrier
        for su_name in self.storage_units.index:
                node_id = su_name.replace(" ", "_")
                style_lines.append(f"style {node_id} {highlight}")

        if style_lines:
            code += "\n  " + "\n  ".join(style_lines)

        return code


    def create_mermaid_output(
        self, graph: str, folderpath: str, return_mermaid_code: bool = False
    ) -> None:
        """
        Render the Mermaid code as a PNG image and save it to *folderpath*.

        Parameters
        ----------
        graph : str
            Mermaid code for the network diagram.
        folderpath : str
            Destination folder for the PNG file.
        return_mermaid_code : bool, optional
            When *True* also saves the raw Mermaid code as a .txt file.

        Notes
        -----
        Requires an internet connection (calls ``https://mermaid.ink``).
        When the graph is too large for the URI-based API the raw code is
        written to a .txt file regardless of *return_mermaid_code*.
        """
        import base64

        import matplotlib.pyplot as plt
        import requests
        from PIL import Image as im

        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        if return_mermaid_code:
            with open(folderpath + "/" + self.carrier + ".txt", "w") as f:
                f.write(graph)

        graphbytes = graph.encode("utf8")
        base64_bytes = base64.urlsafe_b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")
        try:
            img = im.open(
                BytesIO(
                    requests.get("https://mermaid.ink/img/" + base64_string).content
                )
            )
        except UnidentifiedImageError as e:
            with open(folderpath + "/" + self.carrier + ".txt", "w") as f:
                f.write(graph)
            response = requests.get("https://mermaid.ink/img/" + base64_string)
            if response.status_code == 414:
                print(
                    "Carrier "
                    + self.carrier
                    + ": The graph is too large to be visualized by URI. "
                    "Mermaid code saved to file instead."
                )
            else:
                print(response.status_code)
                print(response.text[:500])
                raise Exception("mermaid URI-Error:", str(e))
        else:
            plt.imshow(img)
            plt.axis("off")
            plt.savefig(folderpath + "/" + self.carrier + ".png", dpi=1200)

    def plot_subnetwork(self, folderpath: str, return_mermaid_code: bool = False) -> None:
        """
        Plot the carrier sub-network topology and save it as a PNG.

        Parameters
        ----------
        folderpath : str
            Path to the output folder.
        return_mermaid_code : bool, optional
            When *True* also saves the Mermaid code as a .txt file.

        Notes
        -----
        Requires an internet connection.
        """
        mermaid_code = self.get_mermaid_string()
        self.create_mermaid_output(mermaid_code, folderpath, return_mermaid_code)
