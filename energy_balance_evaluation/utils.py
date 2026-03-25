#!/usr/bin/env python3

import os
from io import BytesIO

import numpy as np
import pandas as pd
import pypsa
from PIL import UnidentifiedImageError


class CarriersNetwork:
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
        self.generators = self.get_generators()
        self.buses = self.get_buses()
        self.links = self.get_links()
        self.lines = self.get_lines()
        self.stores = self.get_stores()
        self.storage_units = self.get_storage_units()
        self.loads = self.get_load()
        if self.buses.empty:
            raise Exception("No buses found for carrier " + self.carrier)
        else:
            self.processes = self.get_all_processes()
            if eval_one_node:
                self.reduce_to_one_node(search_therm)
            if bus_pattern is not None:
                self.filter_by_bus_pattern(bus_pattern)

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

    def get_generators(self) -> pd.DataFrame:
        """Return generators whose carrier matches this carrier."""
        return self.n.generators[self.n.generators.carrier.str.contains(self.carrier)]

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
        Return loads of this carrier.

        Notes
        -----
        Prints a warning when loads have a different carrier than their bus.
        """
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
        Return stores attached to the carrier buses.

        Notes
        -----
        Prints a warning when stores have a different carrier than their bus.
        """
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
        Return storage units attached to the carrier buses.

        Notes
        -----
        Prints a warning when storage units have a different carrier than
        their bus.
        """
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

        Returns
        -------
        list of list of str
            Nested list of Mermaid node / edge definitions.
        """
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
        mermaid_code.append(
            [
                "BUS_"
                + row.bus0.replace(" ", "_")
                + "-- "
                + index
                + " -->BUS_"
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
        # buses and edges from lines
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
                + "-- "
                + index
                + " -->BUS_"
                + row.bus1.replace(" ", "_")
                for index, row in self.lines.iterrows()
            ]
        )
        return mermaid_code

    def get_mermaid_string(self) -> str:
        """
        Return the complete Mermaid flowchart code as a single string.

        Returns
        -------
        str
            Mermaid flowchart code ready to be rendered or saved to a file.
        """
        mermaid_code_list = self.mermaid_carriers_network()
        flat = list(
            set([item for sublist in mermaid_code_list for item in sublist])
        )
        return "flowchart LR;\n  " + "\n  ".join(flat)

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
