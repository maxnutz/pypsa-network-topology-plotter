#!/usr/bin/env python3

import pandas as pd
import numpy as np
import os
from PIL import UnidentifiedImageError

import pypsa

from energy_balance_evaluation.statics import eb_row_string_replacement_dict


class EnergyBalanceAT:
    """
    AT energy balance reader and mapper

    Inputs:
    - year: sheet name (str)
    - path_to_xlsb: path to .xlsb file (str), optional

    Outputs / attributes:
    - df_eb: cleaned energy balance DataFrame (pandas.DataFrame)
    - df_variables: variable mapping DataFrame (pandas.DataFrame)
    - sheet_name: provided sheet name (str)
    - path_to_xlsb: provided file path (str)

    Methods:
    - import_excel: import and initial cleaning
    - create_multiindex_structure: build multi-index and depth column
    - map_variable_names: derive variable names and mappings
    """

    def __init__(
        self,
        year,
        path_to_xlsb="EnergyBalances/BalancesApril2025/AT-Energy-balance-sheets-April2025-edition.xlsb",
        country="AT",
        input_matrix: pd.DataFrame | None = None,
        original_input: bool = True,
    ):
        self.original_input = original_input
        if input_matrix is not None:
            self.df_eb = input_matrix
            self.create_multiindex_structure()
            self.map_variable_names()
        else:
            self.sheet_name = year
            self.path_to_xlsb = path_to_xlsb
            self.country = country
            self.df_eb = self.import_excel()
            self.create_multiindex_structure()
            self.map_variable_names()

    def import_excel(self) -> pd.DataFrame:
        """Imports the energy balance excel sheet and does some initial cleaning."""
        df_eb = pd.read_excel(
            self.path_to_xlsb,
            sheet_name=self.sheet_name,
            skiprows=3,
        )
        df_eb.rename(
            columns={
                "Unnamed: 0": "layer_0",
                "Unnamed: 1": "layer_1",
                "Unnamed: 2": "layer_2",
                "Unnamed: 7": "index",
            },
            inplace=True,
        )
        df_eb.drop(
            columns=["Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
            inplace=True,
        )
        df_eb.loc[0, "index"] = "energycarrier"
        df_eb.loc[1, "layer_0"] = "Total absolute values"
        if self.original_input:
            df_eb.dropna(axis="columns", how="all", inplace=True)
        # Standardize column names by replacing spaces with underscores and stripping surrounding whitespace
        df_eb.columns = [col.replace(" ", "_").strip() for col in df_eb.columns]
        return df_eb

    def create_multiindex_structure(self) -> None:
        """Build a multi-index from layer columns and compute row depth.

        Scans layer_0/1/2 for +/- markers, records them in a '+/-' column,
        replaces marker values with NaN, forward-fills hierarchical labels,
        sets a MultiIndex (layer_0, layer_1, layer_2) and adds a 'depth' column
        indicating the hierarchy level (0..n). Updates self.df_eb in-place.
        """
        try:
            df = self.df_eb.copy()
            df["+/-"] = None
            df["+/-"].astype("str")

            for index, row in df.iterrows():
                if (
                    row["layer_0"] == "+"
                    or row["layer_0"] == "-"
                    or row["layer_0"] == "="
                ):
                    df.at[index, "+/-"] = df.at[index, "layer_0"]
                if (
                    row["layer_1"] == "+"
                    or row["layer_1"] == "-"
                    or row["layer_1"] == "="
                ):
                    df.at[index, "+/-"] = df.at[index, "layer_1"]
                if (
                    row["layer_2"] == "+"
                    or row["layer_2"] == "-"
                    or row["layer_2"] == "="
                ):
                    df.at[index, "+/-"] = df.at[index, "layer_2"]
            layers = [col for col in df.columns if col.startswith("layer_")]
            df[layers] = df[layers].replace(["+", "-", "=", "NaN", "nan"], np.nan)
            df = df.replace("Z", np.nan)

            last_valid_value_1 = df["layer_1"].values[0]
            for index, row in df.iterrows():
                if pd.isna(row["layer_0"]) and pd.isna(row["layer_1"]):
                    df.at[index, "layer_1"] = last_valid_value_1
                if not pd.isna(row["layer_1"]):
                    last_valid_value_1 = row["layer_1"]
            df["layer_0"] = df["layer_0"].ffill()
            df.set_index(["layer_0", "layer_1", "layer_2"], inplace=True, drop=False)

            df["depth"] = np.nan
            df["depth"] = [(sum(pd.notna(x) for x in idx) - 1) for idx in df.index]
        except Exception as e:
            print(f"An error occurred while creating the multiindex structure: {e}")
            raise Exception(e)
        else:
            self.df_eb = df

    def map_variable_names(self) -> None:
        """
        Map variables to AT-Energy-Balance-specific variable names created from Sheets naming.

        This method takes the multi-index structure of the AEB-Sheet and
        maps the hierarchical variable names tospecific variable names
        created from that AEB-Sheet.

        It creates a new column "var_name" by concatenating the hierarchical labels
        of the multilayer index with ">" and sets the index to "var_name" and drops the column.

        The method updates the instance variables self.df_variables and self.df_eb in-place.
        """
        if "+/-" not in self.df_eb.columns:
            print("Need multiindex structure. Creating it first...")
            self.create_multiindex_structure()
        df_var_names = self.df_eb[
            ["layer_0", "layer_1", "layer_2", "index", "+/-", "depth"]
        ].copy()
        layer_0 = df_var_names["layer_0"].copy()
        layer_1 = df_var_names["layer_1"].copy()
        # forward fill layer_0 where layer_0 is NaN or in ["+", "-", "="]
        last_valid_value_0 = layer_0.values[0]
        valid_value_1 = layer_1.values[0]
        for i0, i1 in zip(range(0, len(layer_0.values)), range(0, len(layer_1.values))):
            val0 = layer_0.values[i0]
            val1 = layer_1.values[i1]
            if pd.notna(val0) and val0 not in ["+", "-", "="]:
                last_valid_value_0 = val0
            else:
                layer_0[i0] = last_valid_value_0
                if pd.notna(val1) and val1 not in ["+", "-", "="]:
                    valid_value_1 = layer_1.values[i1]
                else:
                    layer_1[i1] = valid_value_1

        df_var_names["layer_0"] = layer_0.apply(
            lambda x: replace_by_dict(str(x), eb_row_string_replacement_dict)
        )
        df_var_names["layer_1"] = layer_1.apply(
            lambda x: replace_by_dict(str(x), eb_row_string_replacement_dict)
        )
        var_names = []

        for index, row in df_var_names.iterrows():
            if not pd.isna(row["layer_0"]) and row["layer_0"] not in ["+", "-", "="]:
                var_name = row["layer_0"]
                if not pd.isna(row["layer_1"]) and row["layer_1"] not in [
                    "+",
                    "-",
                    "=",
                ]:
                    var_name += "-" + row["layer_1"]
                    if not pd.isna(row["layer_2"]) and row["layer_2"] not in [
                        "+",
                        "-",
                        "=",
                    ]:
                        var_name += "-" + replace_by_dict(
                            row["layer_2"], eb_row_string_replacement_dict
                        )
            elif not pd.isna(row["layer_1"]) and row["layer_1"] not in ["+", "-", "="]:
                var_name = row["layer_1"]
                if not pd.isna(row["layer_2"]) and row["layer_2"] not in [
                    "+",
                    "-",
                    "=",
                ]:
                    var_name += "-" + replace_by_dict(
                        row["layer_2"], eb_row_string_replacement_dict
                    )
            elif not pd.isna(row["layer_2"]) and row["layer_2"] not in ["+", "-", "="]:
                var_name = row["layer_2"]
            else:
                var_name = None
            var_names.append(var_name)
        df_var_names["var_name"] = var_names
        df_variables = df_var_names[["var_name", "index", "+/-"]].set_index(
            "var_name", drop=True
        )
        self.df_variables = df_variables
        self.df_eb["var_name"] = df_var_names["var_name"]

    def select(
        self,
        search_string: str | None = None,
        depth: int | None = None,
        only_return_index: bool = False,
        drop_multilayer: bool = False,
    ) -> pd.DataFrame:
        """
        Search for given string of any hierachical layer in multiindex
        ---
        Arguments:
        - search_string: string to search for (str, default: None)
        - depth: depth level to filter by (int, default: None)
        - only_return_index: only return index values (bool, default: False)
        - drop_multilayer: drop multi-layer structure and return flat DataFrame (bool, default: False)
        **Ether search_string or depth must be provided.**
        ---
        Returns:
        - matching rows as pandas DataFrame.
        - ValueError if no matches found.
        """
        found = []
        if search_string is None and depth is None:
            raise ValueError("Either search_string or depth must be provided.")
        if search_string != None:
            for tuples in self.df_eb.index:
                for strings in tuples:
                    if strings == search_string:
                        found.append(tuples)
            if found:
                df = self.df_eb.T[found].T
            else:
                msg = "No matches found for string '{search_string}'".format(
                    search_string=search_string
                )
                raise ValueError(msg)
        else:
            df = self.df_eb.copy()
        if depth != None:
            df = df[df["depth"] == depth]

        if only_return_index:
            if drop_multilayer:
                return df.var_name.values
            return df.index.values
        if drop_multilayer:
            return df.set_index("var_name").drop(
                columns=["layer_0", "layer_1", "layer_2"]
            )
        return df


class CarriersNetwork:
    def __init__(
        self,
        carrier: str,
        n: pypsa.Network,
        eval_one_node: bool = False,
        search_therm: bool | str = None,
    ):
        """
        Initialises the CarriersNetwork class.
        ---
        Parameters
        carrier : str
            The name of the carrier for which the network should be evaluated.
        eval_one_node : bool, optional
            Whether to reduce the network to one node. Defaults to False.
        search_therm : bool | str, optional
            The search term to be used when reducing the network to one node. Defaults to None.
        n : pypsa.Network, optional
            The network object to be evaluated. Defaults to n.
        ---
        Attributes
        carrier : str
            The name of the carrier for which the network should be evaluated.
        n : pypsa.Network
            The network object to be evaluated.
        generators : pandas.DataFrame
            A DataFrame containing the generators of the carrier.
        buses : pandas.DataFrame
            A DataFrame containing the buses of the carrier.
        links : pandas.DataFrame
            A DataFrame containing the links of the carrier.
        lines : pandas.DataFrame
            A DataFrame containing the lines of the carrier.
        stores : pandas.DataFrame
            A DataFrame containing the stores of the carrier.
        storage_units : pandas.DataFrame
            A DataFrame containing the storage units of the carrier.
        loads : pandas.DataFrame
            A DataFrame containing the loads of the carrier.
        processes : pandas.DataFrame
            A DataFrame containing the processes of the carrier.
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

    def reduce_to_one_node(self, search_therm):
        """
        Reduces the network of the current carrier to one node of the original network.
        ---
        Input:
        - search_therm: name of the node to search for (eg. AT0)
        to find buses, the carrier name is added to the given search string
        ---
        Output:
        - overwrites the attributes of the class reduced to one network node
        """
        self.get_search_therms(search_therm)
        # generators
        self.generators = self.generators[
            self.generators.bus.str.contains(self.search_node)
        ]
        # buses
        self.buses = self.buses[self.buses.index.str.contains(self.search_node)]
        # links
        self.links = pd.concat(
            [
                self.links[self.links.bus0.str.contains(self.search_string)],
                self.links[self.links.bus1.str.contains(self.search_string)],
                self.links[self.links.bus2.str.contains(self.search_string)],
            ]
        )
        # lines
        self.lines = pd.concat(
            [
                self.lines[self.lines.bus0.str.contains(self.search_string)],
                self.lines[self.lines.bus1.str.contains(self.search_string)],
            ]
        )
        # stores
        self.stores = self.stores[self.stores.bus.str.contains(self.search_node)]
        # storage units
        self.storage_units = self.storage_units[
            self.storage_units.bus.str.contains(self.search_node)
        ]
        # loads
        self.loads = self.loads[self.loads.bus.str.contains(self.search_node)]
        self.processes = self.get_all_processes()

    def get_search_therms(self, search_therm):
        """
        Creates the search strings to find all components
        - of the current carrier and the reduced network node.
        - takes first node of the network, if no string is given
        ---
        Output:
        - writes class parameters search_string and search_node
        - no return
        """
        if search_therm:
            self.search_node = search_therm + " " + self.carrier
            self.search_string = search_therm
        else:
            self.search_node = self.buses.index.unique()[0].replace(
                " " + self.carrier, ""
            )
            self.search_string = self.buses.index.unique()[0]

    def get_generators(self):
        return self.n.generators[self.n.generators.carrier.str.contains(self.carrier)]

    def get_buses(self):
        """
        Gets the buses of the classes carrier.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the buses of the carrier.
        Notes
        If there are buses with no generator attached, a warning message is printed.
        """
        buses_carrier = self.n.buses[self.n.buses.carrier.str.contains(self.carrier)]
        buses_with_no_generator = set(
            self.n.generators[
                self.n.generators.carrier.str.contains(self.carrier)
            ].bus.values
        ) - set(buses_carrier.index.values)
        if (
            buses_with_no_generator and buses_carrier.empty
        ):  # TODO: include more buses with query for generators?
            print(
                "There are generators with carrier "
                + self.carrier
                + " attached to a bus with different carrier. Adapt buses query to 'self.n.buses[self.n.buses.generator.str.contains(self.carrier)'"
            )
            buses_carrier = self.n.buses[
                self.n.buses.generator.str.contains(self.carrier)
            ]
        return buses_carrier

    def get_links(self):
        """
        Gets the links of the classes carriers busses and corresponding ones.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the links of the carrier.
        """
        return pd.concat(
            [
                self.n.links[self.n.links.bus0.isin(self.buses.index)],
                self.n.links[self.n.links.bus1.isin(self.buses.index)],
                self.n.links[self.n.links.bus2.isin(self.buses.index)],
            ]
        )

    def get_lines(self):
        """
        Gets the lines of the classes carriers busses and corresponding ones.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the lines of the carrier.
        """
        return pd.concat(
            [
                self.n.lines[self.n.lines.bus0.isin(self.buses.index)],
                self.n.lines[self.n.lines.bus1.isin(self.buses.index)],
            ]
        )

    def get_load(self):
        """
        Gets the loads of the classes carrier.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the loads of the carrier.
        Notes
        If loads have divverent carriers as buses, they are attached to, a warning message is printed.
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
            print(
                "  used query for data: self.n.loads[self.n.loads.bus.isin(self.buses.index)]"
            )
            return self.n.loads[self.n.loads.bus.isin(self.buses.index)]
        return direct_load_of_carrier

    def get_stores(self):
        """
        Gets the stores of the classes carrier attached to the carriers busses.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the stores of the carrier.
        Notes
        If stores have divverent carriers as buses, they are attached to, a warning message is printed.
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

    def get_storage_units(self):
        """
        Gets the storage units of the classes carrier attached to the carriers busses.
        ---
        Returns
        pandas.DataFrame
            A DataFrame containing the storage units of the carrier.
        Notes
        unlikely, that it returns elements, as storage units are connected to their own busses
        If storage units have divverent carriers as buses, they are attached to, a warning message is printed.
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
            return self.n.storage_units[self.n.storage_units.bus.isin(self.buses.index)]
        return storage_units_carrier

    def get_all_processes(self):
        link_processes_of_carrier = self.links.carrier.unique()
        line_processes_of_carrier = self.lines.carrier.unique()
        return np.append(link_processes_of_carrier, line_processes_of_carrier)

    def mermaid_carriers_network(self) -> list:
        """
        Creates network diagram in mermaid code for the classes sub-network
        ---
        Input:
        - all class variables directly read from pypsa network are needed
        ---
        Output:
        - mermaid code for network diagram as list of strings.
        """
        mermaid_code = []
        # add all main buses
        mermaid_code.append(
            [
                "BUS_" + val.replace(" ", "_") + "(((" + val + ")))"
                for val in self.buses.index.values
            ]
        )

        # add all generators
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

        # add all loads
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

        # add all storage_units
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

        # add all links and all buses, links to go
        list_of_buses = (
            list(self.links.bus0.values)
            + list(self.links.bus1.values)
            + list(self.links.bus2.values)
        )
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
        mermaid_code.append(
            [
                "BUS_"
                + row.bus0.replace(" ", "_")
                + "-- "
                + index
                + " indirect -->BUS_"
                + row.bus2.replace(" ", "_")
                for index, row in self.links.iterrows()
                if row.bus2 != ""
            ]
        )

        # add all lines and all buses, lines go to
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

    def create_mermaid_output(
        self, graph: str, folderpath: str, return_mermaid_code: bool = False
    ):
        """
        Creates an image of the network diagram from the given mermaid code.
        Input:
        ---
        graph : str
            The mermaid code for the network diagram.
        folderpath : str
            The path to the folder where the image should be saved.
        internet-connection needed
        Returns
        ---
        file is saved as jpg with carriers name.
        """
        import base64
        import io, requests
        from IPython.display import Image, display
        from PIL import Image as im
        import matplotlib.pyplot as plt

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
                io.BytesIO(
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
                    + ": The graph is too large to be visualized by URI. Save mermaid code to file instead"
                )
            else:
                print(response.status_code)
                print(response.text[:500])
                raise Exception("mermaid URI-Error:", str(e))
        else:
            plt.imshow(img)
            plt.axis("off")  # allow to hide axis
            plt.savefig(folderpath + "/" + self.carrier + ".png", dpi=1200)

    def plot_subnetwork(self, folderpath: str, return_mermaid_code=False):
        """
        Plots the sub-network of the classes carrier attached to the carriers busses.
        Input:
        ---
        - folderpath: path to outputfolder
        - return_mermaid_code: boolean - if True, saves mermaid code to textfile.
        - needs internet connection to call create_mermaid_output
        Output:
        ---
        - mermaid code for network diagram as list of strings is created
        - an image of the network diagram from the given mermaid code is created
        internet-connection needed
        Returns
        ---
        file is saved as jpg with carriers name
        """
        mermaid_code_list = self.mermaid_carriers_network()
        mermaid_code_list = list(
            set([string for submermaid in mermaid_code_list for string in submermaid])
        )
        mermaid_code = "flowchart LR;\n  " + "\n  ".join(mermaid_code_list)
        self.create_mermaid_output(
            f"""{mermaid_code}""", folderpath, return_mermaid_code
        )


def extract_true_keys(d: dict, prefix="") -> list:
    """
    Recursively traverses a dictionary, creates exact identification values
    from dict structure and returns a list of keys that have a value of True.

    Parameters:
    -----------
    d : dict
        The dictionary to traverse.
    prefix : str, optional
        A prefix to add to the keys in the returned list. Defaults to "".

    Returns:
    --------
    list: A list of keys with values of True.
    """
    keylist = []
    for key, value in d.items():
        current_path = f"{prefix}>{key}" if prefix else key

        if isinstance(value, bool):
            if value:
                # Drop ">nan" if current key is "nan"
                keylist.append(prefix if key == "nan" else current_path)

        elif isinstance(value, dict):
            keylist.extend(extract_true_keys(value, current_path))
    return keylist


def replace_by_dict(string: str, replacement_dict: dict) -> str:
    """
    Replaces all occurrences of each key in the given string with the corresponding value in the replacement_dict.

    Parameters:
    ----------
    string : str
        The string to replace substrings in.
    replacement_dict : dict
        A dictionary containing the strings to replace as keys and their replacements as values.

    Returns:
    -------
    str:
        The string with all occurrences of each key replaced.
    """
    for key, value in replacement_dict.items():
        string = string.replace(key, value)
    return string


def main():
    print("This will be a test of the module for energy balance evaluation.")
    try:
        cs = EnergyBalanceAT("2023")
    except Exception as e:
        print(f"An error occurred while creating the EnergyBalanceAT instance: {e}")


if __name__ == "__main__":
    main()
