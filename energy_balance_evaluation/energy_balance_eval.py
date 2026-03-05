#!/usr/bin/env python3

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import gzip
import warnings
from urllib.request import urlopen


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
            yaml-filepath where the output will be written to - path will be extended by year
            used for validation data in init. eg. filepath.yaml -> filepath_2020.yaml
        country : str, optional
            Country code to filter data (default: 'AT' for Austria)
        """
        self.name = set_name
        self.year = year
        self.filepath_definition = filepath_definition
        self.filepath_codelist = filepath_codelist[:-5] + "_" + str(year) + ".yaml"
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

    def calculate_variable_values(
        self, filepath_tsv: str | None = None
    ) -> dict:  # only valid for old structure
        """
        Calculate variable values by querying the TSV file.

        For each variable, queries the TSV file for rows matching the specified
        nrg and siec codes for the given country and year, then sums the values.

        Parameters
        ----------
        filepath_tsv : str | None, optional
            overwrites the default filepath and prevents from API download if file exists

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
            self.tsv_data = fetch_and_load_tsv_data(filepath_tsv)

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
            df_filtered = df[
                df["nrg_bal"].isin(nrg_codes) & df["siec"].isin(siec_codes)
            ]

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

        # Data retrieval/loading is handled by fetch_and_load_tsv_data via
        # calculate_variable_values
        calculated_values = self.calculate_variable_values(filepath_tsv)

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


def fetch_and_load_tsv_data(filepath_tsv: str | None = None) -> pd.DataFrame:
    """
    Load and parse Eurostat energy balance TSV data.

    The function first looks for `resources/estat_nrg_bal_c.tsv`.
    If that file does not exist, it is downloaded from the Eurostat API
    and saved to the resources folder before loading.

    Parameters
    ----------
    filepath_tsv : str | None, optional
        overwrites the default filepath. If file does not exist, API download
        saves to that location.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: freq, nrg_bal, siec, unit, geo, and year columns
    """
    resource_path = Path("resources/estat_nrg_bal_c.tsv")
    api_url = (
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
        "nrg_bal_c?format=TSV&compressed=true"
    )
    if filepath_tsv is not None:
        resource_path = Path(filepath_tsv)
    if not resource_path.exists():
        warning_msg = (
            "resources/estat_nrg_bal_c.tsv not found. Downloading from Eurostat API; "
            "this can take some time."
        )
        warnings.warn(warning_msg, UserWarning)
        print(f"WARNING: {warning_msg}")

        resource_path.parent.mkdir(parents=True, exist_ok=True)

        with urlopen(api_url) as response:
            payload = response.read()

        # `compressed=true` returns gzip-compressed bytes.
        # Fallback to plain UTF-8 content if decompression fails.
        try:
            content = gzip.decompress(payload).decode("utf-8")
        except OSError:
            content = payload.decode("utf-8")

        resource_path.write_text(content, encoding="utf-8")

    # Read TSV file, treating the header specially
    df = pd.read_csv(resource_path, sep=",|\t", dtype=str, engine="python")

    # The first column header is 'freq,nrg_bal,siec,unit,geo\TIME_PERIOD'
    # We need to properly split this
    first_col = df.columns[0]
    if "freq" in first_col and "nrg_bal" in first_col:
        # Header is malformed, need to read differently
        df = pd.read_csv(filepath_tsv, sep="\t", dtype=str, skiprows=1)

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
                df[year_col].replace(":", np.nan), errors="coerce"
            )
    df = df[df["unit"] == "GWH"]
    return df


def main():
    print("This is a unit test of the energy_balance_eval")

    final_energy = VariablesSet(
        set_name="final_energy",
        year=2020,
        filepath_definition="definitions/variable/final_energy.yaml",
        filepath_codelist="validate_data/final_energy.yaml",
        country="AT",
    )

    final_energy.write_codelist()


if __name__ == "__main__":
    main()
