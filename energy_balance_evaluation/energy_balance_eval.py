#!/usr/bin/env python3

import pandas as pd
import numpy as np
import yaml
from pathlib import Path

from energy_balance_evaluation.utils import EnergyBalanceReader, read_mapping_csv
from energy_balance_evaluation import (
    extract_true_keys,
    non_numerical_columns_list,
    rows_to_add_dict,
    rows_to_include_dict,
)


class EnergyBalance(EnergyBalanceReader):
    """
    Class for evaluating the energy balance data

    Contains methods for selecting data based on hierarchical depth and search strings.

    Attributes:
    ----------
    - year: year of the energy balance data to evaluate (int)
    - path_to_xlsb: path to the Excel file containing the energy balance data (str)
    - country: country of the energy balance data (str)
    - input_matrix: input DataFrame containing the energy balance data (pandas.DataFrame | None)
    - original_input: flag indicating whether to use the original input DataFrame or a modified version (bool)

    Methods:
    -------
    - get_top_layer_entries: get all top layer entries with number values
    - get_entries_of_category: get all entries of a given category

    """

    def __init__(
        self,
        year: str,
        path_to_xlsb: str = "EnergyBalances/BalancesApril2025/AT-Energy-balance-sheets-April2025-edition.xlsb",
        filepath_mapping_csv: str = "resources/carrier_mapping_energy_balance.csv",
        country: str = "AT",
        input_matrix: pd.DataFrame | None = None,
        original_input: bool = True,
    ):
        super().__init__(year, path_to_xlsb, country, input_matrix, original_input)
        self.filepath_mapping_csv = filepath_mapping_csv

    def get_top_layer_entries(self, only_total_values: bool = False) -> pd.DataFrame:
        """
        Get all top layer entries with number values.
        Inputs:
        - only_total_values: only return column TOTAL
        Outputs:
        - pandas.DataFrame
        """
        df = self.select(
            depth=0,
            only_return_index=False,
        )[:-1]
        if only_total_values:
            return df[["TOTAL"]]
        return df

    def get_entries_of_category(
        self,
        category: str,
        only_total_values: bool = False,
        drop_multilayer: bool = False,
    ) -> pd.DataFrame:
        """
        Get all entries of a given category.
        ---
        Inputs:
        - category: one of the top layer categories (string)
        - only_total_values: only return column TOTAL (bool)
        - drop_multilayer: drop multi-layer structure and return flat DataFrame (bool)
        ---
        Outputs:
        - pandas.DataFrame
        """
        df = self.select(
            search_string=category,
            depth=1,
            only_return_index=False,
        )[:-1]
        if drop_multilayer:
            df = self.select(
                search_string=category,
                depth=1,
                only_return_index=False,
                drop_multilayer=True,
            )[:-1]
        if only_total_values:
            return df[["TOTAL"]]
        return df

    def reduce_energy_balance_by_rows(self) -> pd.DataFrame:
        """
        Reduce an EnergyBalance object to a subset of rows by selecting based on the defined
        dict in static (rows_to_include_dict) and summing up rows according to the rows_to_add_dict.

        Returns
        -------
        pd.DataFrame
            A pandas DataFrame containing the reduced EnergyBalance data.
        """
        list_var_names_to_include = extract_true_keys(rows_to_include_dict)
        df_light = self.df_eb[
            self.df_eb["var_name"].isin(list_var_names_to_include)
        ].copy()

        # sum rows to concatenate and create new rows index
        # - therefore split in numerical and non-numerical parts
        # - transpose for easy summing of corresponding rows
        # - recombine afterwards and remove unnecessary rows
        added_rows_specs = {
            key: {f"layer_{i}": part for i, part in enumerate(key.split(">"))}
            for key in rows_to_add_dict
        }
        df_light.set_index("var_name", inplace=True, drop=False)
        df_light_numerical = df_light.loc[
            :,
            ~df_light.columns.isin(non_numerical_columns_list),
        ]
        df_light_non_numerical = df_light.loc[
            :,
            df_light.columns.isin(non_numerical_columns_list),
        ]
        df_light_numerical_T = df_light_numerical.T
        # Sum specified rows (given by `rows_to_add_dict`) into new aggregated rows.
        # Be defensive: entries in `rows_to_add_dict` may be lists, Index objects
        # or other array-like types and may not match column labels exactly
        # (e.g., whitespace differences). Try to match available columns and
        # provide a helpful error message if nothing can be matched.
        for key, value in rows_to_add_dict.items():
            # normalize value to a list of strings
            if isinstance(value, (str, bytes)):
                vals = [value]
            else:
                try:
                    vals = list(value)
                except Exception:
                    raise Exception()
                    vals = [value]

            # find columns that match the requested values
            cols_to_sum = [c for c in df_light_numerical_T.columns if c in vals]

            # try a relaxed match (strip whitespace) if none found
            if not cols_to_sum:
                stripped_vals = [v.strip() if isinstance(v, str) else v for v in vals]
                cols_to_sum = [
                    c for c in df_light_numerical_T.columns if c in stripped_vals
                ]

            if not cols_to_sum:
                raise KeyError(
                    f"Rows to add '{key}' reference missing columns {vals!r} in the transposed numeric df. "
                    f"Available columns (first 20): {list(df_light_numerical_T.columns[:20])!r}"
                )

            df_light_numerical_T[key] = df_light_numerical_T[cols_to_sum].sum(axis=1)
        df_light_numerical = df_light_numerical_T.T
        df_light_all = pd.concat(
            [df_light_numerical, df_light_non_numerical], axis=1, join="outer"
        )
        rows_to_delete = [
            item for sublist in rows_to_add_dict.values() for item in sublist
        ]
        df_light_all = df_light_all[~df_light_all.index.isin(rows_to_delete)]

        df_light_all["var_name"] = df_light_all.index
        # add layer-entries for new summed up rows
        for row, layer_dict in added_rows_specs.items():
            for layer, value in layer_dict.items():
                df_light_all.loc[row, layer] = value
        df_light_all.sort_values(["layer_0", "layer_1", "layer_2"], inplace=True)
        df_light_all.set_index(
            ["layer_0", "layer_1", "layer_2"], inplace=True, drop=False
        )
        return df_light_all

    def reduce_energy_balance_by_columns(
        self, df: pd.DataFrame, mapping_eb_pypsa: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Reduce the energy balance dataframe by summing up columns
        according to a given mapping between eb_index and pypsa-entry.

        Parameters
        ----------
        df : pd.DataFrame
            The energy balance dataframe to be reduced.
        mapping_eb_pypsa : pd.DataFrame
            A dataframe containing the mapping between eb_index
            and pypsa-entry.

        Returns
        -------
        pd.DataFrame
            A reduced energy balance dataframe containing the summed up columns.
        """
        # create mapping between eb_index and pypsa-entry and create sum of respective columns
        mapping_eb_pypsa_sum = mapping_eb_pypsa.copy().set_index(
            "pypsa-entry", drop=True
        )
        mapping_eb_pypsa_dict = (
            mapping_eb_pypsa_sum.groupby(mapping_eb_pypsa_sum.index)
            .agg(list)["eb_index"]
            .to_dict()
        )
        for pypsa_key, eb_list in mapping_eb_pypsa_dict.items():
            df[pypsa_key] = df[eb_list].sum(axis=1)
        df_red_pypsa_columns = df.loc[
            :,
            df.columns.isin(
                non_numerical_columns_list + list(mapping_eb_pypsa_dict.keys())
            ),
        ]
        return df_red_pypsa_columns

    def create_reduced_energy_balance(self) -> pd.DataFrame:
        """
        Creates a reduced version of the eurostat energy balance from the
        given file path and the mapping between eb_index and pypsa-entry.

        Parameters
        ----------
        self : object
            The object containing the file paths and the mapping.

        Inputfiles:
        -----------
        resources/carrier_mapping_energy_balance.csv: holding the mapping of
            pypsa-carriers with the energy balance carriers

        Returns
        -------
        pd.DataFrame
            A reduced energy balance dataframe containing the summed up columns.
        """
        # index_to_nicenames = eb.df_eb.iloc[0, :].to_dict()
        # pe_carrier_nicenames_to_index = {
        #     val: key for key, val in index_to_nicenames.items()
        # }
        mapping_eb_pypsa = read_mapping_csv(self.filepath_mapping_csv)
        df_light_rows = self.reduce_energy_balance_by_rows()
        df_light = self.reduce_energy_balance_by_columns(
            df=df_light_rows, mapping_eb_pypsa=mapping_eb_pypsa
        )
        return df_light

    def populate_dict_from_eb_input(self) -> None:
        """
        Reads from the reduced version of the eurostat energy balance to
        populate the dict eval_dict for the respective primary energy carrier.
        """
        pass


class VariablesSet:
    def __init__(
        self,
        set_name: str,
        year: int,
        filepath_definition: str,
        filepath_codelist: str,
        country: str = "AT",
    ) -> None:
        """
        Initialize a VariablesSet to read, calculate, and write variable codelists.

        Parameters
        ----------
        set_name : str
            Name of the variable set (e.g., 'final_energy')
        year : int
            Year for which to calculate values - integer. converted to string for csv-readup.
        filepath_definition : str
            Path to the YAML file containing variable definitions
        filepath_codelist : str
            Path where the output codelist YAML file will be written
        country : str, optional
            Country code to filter data (default: 'AT' for Austria)
        """
        self.name = set_name
        self.year = year
        self.filepath_definition = filepath_definition
        self.filepath_codelist = filepath_codelist
        self.country = country
        self.variables_dict = None  # Cache for parsed YAML
        self.tsv_data = None  # Cache for TSV data

    def read_yaml_file(self) -> dict:
        """
        Read and parse variable definitions from YAML file.

        Returns
        -------
        dict
            Dictionary with variable names as keys and metadata dicts as values.
            Example: {
                'Final Energy': {
                    'description': '...',
                    'unit': 'GWh',
                    'nrg': 'FC_E',
                    'siec': 'TOTAL',
                    'value': 279335.902
                },
                ...
            }

        Raises
        ------
        FileNotFoundError
            If the YAML definition file does not exist.
        yaml.YAMLError
            If the YAML file cannot be parsed.
        ValueError
            If the YAML structure is not as expected.
        """
        try:
            with open(self.filepath_definition, 'r') as f:
                variables_list = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Variable definition file not found: {self.filepath_definition}"
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Failed to parse YAML file {self.filepath_definition}: {str(e)}"
            ) from e

        if not isinstance(variables_list, list):
            raise ValueError(
                f"Expected YAML file to contain a list, got {type(variables_list).__name__}"
            )

        # Convert list of dicts to dict with variable names as keys
        self.variables_dict = {}
        for item in variables_list:
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected each YAML list item to be a dict, got {type(item).__name__}"
                )
            # Each item should be a dict with one key (variable name)
            for var_name, var_metadata in item.items():
                self.variables_dict[var_name] = var_metadata

        return self.variables_dict

    def _parse_codes(self, code_string: str) -> list:
        """
        Parse code string into list of individual codes.

        Handles:
        - Single codes: 'FC_E' → ['FC_E']
        - Multiple codes: 'FC_OTH_HH_E,FC_OTH_CP_E' → ['FC_OTH_HH_E', 'FC_OTH_CP_E']
        - Comments: 'FC_E  # comment' → ['FC_E']

        Parameters
        ----------
        code_string : str
            Code string with optional comma separation and comments

        Returns
        -------
        list
            List of individual codes (stripped and comment-free)
        """
        # Remove comments (text after #)
        if '#' in code_string:
            code_string = code_string.split('#')[0]

        # Split by comma and strip whitespace
        codes = [code.strip() for code in code_string.split(',')]
        return [code for code in codes if code]  # Remove empty strings

    def _load_tsv_data(self, filepath_tsv: str) -> pd.DataFrame:
        """
        Load and parse TSV file with Eurostat energy balance data.

        Parameters
        ----------
        filepath_tsv : str
            Path to the TSV file

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: freq, nrg_bal, siec, unit, geo, and year columns
        """
        # Read TSV file, treating the header specially
        df = pd.read_csv(filepath_tsv, sep=",|\t", dtype=str, engine="python")

        # The first column header is 'freq,nrg_bal,siec,unit,geo\TIME_PERIOD'
        # We need to properly split this
        first_col = df.columns[0]
        if 'freq' in first_col and 'nrg_bal' in first_col:
            # Header is malformed, need to read differently
            df = pd.read_csv(
                filepath_tsv,
                sep='\t',
                dtype=str,
                skiprows=1
            )

        # Strip whitespace from column names which can appear in the
        # pypsa-eur-download format (e.g. ' 1990 ' or
        # 'geo\TIME_PERIOD').  This makes later column lookups much simpler.
        df.columns = [col.strip() for col in df.columns]

        # If the special combined geo column is present, rename it to 'geo'
        # so that downstream code can always reference df['geo'].
        # NOTE: the backslash must be escaped in the literal string.
        if "geo\\TIME_PERIOD" in df.columns and "geo" not in df.columns:
            df.rename(columns={"geo\\TIME_PERIOD": "geo"}, inplace=True)

        # Set column names properly (after renaming) for later logic
        col_names = list(df.columns)

        # Convert numeric columns to float, handling ':' as missing
        # Years are expected after the first five columns
        year_columns = col_names[5:]
        for year_col in year_columns:
            if year_col in df.columns:
                df[year_col] = pd.to_numeric(
                    df[year_col].replace(':', np.nan), errors='coerce'
                )

        return df

    def calculate_variable_values(self, filepath_tsv: str) -> dict:
        """
        Calculate variable values by querying the TSV file.

        For each variable, queries the TSV file for rows matching the specified
        nrg and siec codes for the given country and year, then sums the values.

        Parameters
        ----------
        filepath_tsv : str
            Path to the pypsa-eur-download.tsv file

        Returns
        -------
        dict
            Dictionary with variable names as keys and calculated values as values.
            Example: {'Final Energy': 279335.902, 'Final Energy|Electricity': 63260.630, ...}
        """
        if self.variables_dict is None:
            self.read_yaml_file()

        # Load TSV data (cache it)
        if self.tsv_data is None:
            self.tsv_data = self._load_tsv_data(filepath_tsv)

        df = self.tsv_data.copy()

        # Filter by country - expect a column named 'geo' after loading.
        if "geo" not in df.columns:
            raise KeyError(
                "TSV data did not contain a 'geo' column after loading. "
                f"Available columns: {list(df.columns)[:10]}"
            )
        df = df[df['geo'] == self.country]

        calculated_values = {}

        for var_name, var_metadata in self.variables_dict.items():
            nrg = var_metadata.get('nrg', '')
            siec = var_metadata.get('siec', '')

            # Parse codes
            nrg_codes = self._parse_codes(nrg)
            siec_codes = self._parse_codes(siec)

            # Special handling for 'TOTAL' siec code
            if 'TOTAL' in siec_codes:
                # When siec is 'TOTAL', match rows where siec is 'TOTAL'
                df_filtered = df[df['nrg_bal'].isin(nrg_codes) & (df['siec'] == 'TOTAL')]
            else:
                # Match rows where siec matches any of the specified codes
                df_filtered = df[df['nrg_bal'].isin(nrg_codes) & df['siec'].isin(siec_codes)]

            # Get the value for the specified year
            if str(self.year) in df_filtered.columns:
                values = df_filtered[str(self.year)].sum(skipna=True)
                calculated_values[var_name] = float(values) if values != 0 else 0.0
            else:
                calculated_values[var_name] = np.nan

        return calculated_values

    def write_codelist(self, filepath_tsv: str | None = None) -> None:
        """
        Writing out variables of the following form:
        - variable: <variable_name>
            year: <self.year>
            value : <value, calculated with self.calculate_variable_values()>
            validation:
                - rtol: 0.3
                - warning_level: low
                  rtol: 0.1
        """
        if self.variables_dict is None:
            self.read_yaml_file()

        # Calculate values if filepath_tsv is provided, otherwise expect values to exist
        if filepath_tsv is not None:
            calculated_values = self.calculate_variable_values(filepath_tsv)
        else:
            # Try to infer the path from typical project structure
            cwd = Path(self.filepath_definition).parent.parent.parent
            inferred_tsv = cwd / 'resources' / 'pypsa-eur-download.tsv'
            if inferred_tsv.exists():
                calculated_values = self.calculate_variable_values(str(inferred_tsv))
            else:
                raise FileNotFoundError(
                    f"filepath_tsv not provided and could not infer from project structure"
                )

        # Build output codelist
        codelist = []
        for var_name, var_metadata in self.variables_dict.items():
            value = calculated_values.get(var_name, 0.0)

            entry = {
                "variable": var_name,
                "year": self.year,  # write as integer value
                "value": round(value, 3),  # Round to 3 decimal places
                "validation": [{"rtol": 0.3}, {"warning_level": "low", "rtol": 0.1}],
            }
            codelist.append(entry)

        # Write to YAML file
        output_path = Path(self.filepath_codelist)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            yaml.dump(
                codelist,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )


def main():
    print("This is a unit test of the energy_balance_eval")

    # eb = EnergyBalance(
    #     year=2023,
    #     path_to_xlsb="resources/EnergyBalances/BalancesFebruary2026/AT-Energy-balance-sheets-February2026-edition.xlsb",
    #     filepath_mapping_csv="resources/carrier_mapping_energy_balance.csv",
    #     country="AT",
    #     original_input=True,
    # )
    # eb.create_reduced_energy_balance()

    final_energy = VariablesSet(
        set_name="final_energy",
        year=2020,
        filepath_definition="definitions/variable/final_energy.yaml",
        filepath_codelist="definitions/validation/final_energy.yaml",
        country="AT",
    )

    final_energy.write_codelist()


if __name__ == "__main__":
    main()
