#!/usr/bin/env python3
"""
pypsa_network_eval – CLI and API for pypsa network topology visualisation.

Usage (command line)
--------------------
    pypsa-topology <path_to_pypsa_file> <carrier> [--bus-pattern PATTERN]
                   [--plot-mermaid {True,False}]

    Multiple carriers can be supplied as a JSON list:
        pypsa-topology network.nc '["gas", "coal"]'

    or

    python -m energy_balance_evaluation.pypsa_network_eval <path_to_pypsa_file> <carrier>

The Mermaid code is always written to resources/<carrier>.txt relative to the
current working directory.  A PNG render is attempted and saved as
resources/<carrier>.png when the diagram is not too large (unless
--plot-mermaid False is given).
"""

import argparse
import json
from pathlib import Path

import pypsa

from .utils import CarriersNetwork, get_components_of_carrier


class CarrierNetwork(CarriersNetwork):
    """
    Evaluate and optionally visualise the sub-network for a single carrier.

    Parameters
    ----------
    carrier : str
        Name of the carrier to evaluate.
    n : pypsa.Network
        Network to evaluate.
    eval_one_node : bool, optional
        Reduce the network to one geographical node. Defaults to False.
    search_therm : bool or str, optional
        Node identifier used when *eval_one_node* is True. Defaults to None.
    bus_pattern : str or None, optional
        When provided, only buses whose index contains *bus_pattern* (and all
        components connected to those buses) are included in the topology.
        Defaults to None (no filtering).
    png_outputfolder_path : str, optional
        Folder where the PNG topology plot is saved.  Required when
        *plot_subnetwork* is True.
    plot_subnetwork : bool, optional
        When True, generate and save a PNG plot of the sub-network topology.
        Defaults to True.
    return_mermaid_code : bool, optional
        When True, also save the raw Mermaid code alongside the PNG.
        Defaults to False.
    """

    def __init__(
        self,
        carrier: str,
        n: pypsa.Network,
        eval_one_node: bool = False,
        search_therm: bool | str = None,
        bus_pattern: str | None = None,
        png_outputfolder_path: str = None,
        plot_subnetwork: bool = True,
        return_mermaid_code: bool = False,
    ):
        super().__init__(carrier, n, eval_one_node, search_therm, bus_pattern)
        if plot_subnetwork:
            if png_outputfolder_path is None:
                raise ValueError(
                    "When plotting subnetworks you must provide the path to an output "
                    "folder via the 'png_outputfolder_path' argument."
                )
            self.plot_subnetwork(png_outputfolder_path, return_mermaid_code)

    def __repr__(self) -> str:
        vars_hint = (
            " -- access attributes: generators, buses, links, lines, stores, "
            "storage_units, loads, processes."
        )
        return f"CarrierNetwork(carrier={self.carrier})" + vars_hint


def eval_all_networks(
    n: pypsa.Network,
    png_outputfolder_path: str,
    eval_one_node: bool = True,
    return_mermaid_code: bool = False,
) -> list:
    """
    Evaluate all carriers in *n* and save topology plots.

    Parameters
    ----------
    n : pypsa.Network
        Network to evaluate.
    png_outputfolder_path : str
        Folder where the PNG topology plots are saved.
    eval_one_node : bool, optional
        Reduce each sub-network to one node. Defaults to True.
    return_mermaid_code : bool, optional
        Also save the Mermaid code for each carrier. Defaults to False.

    Returns
    -------
    list of str
        Carriers for which the evaluation failed.
    """
    error_carriers = []
    for carrier in n.carriers.index.values:
        if carrier in ("none", "", " "):
            continue
        try:
            CarrierNetwork(
                carrier,
                n,
                eval_one_node=eval_one_node,
                png_outputfolder_path=png_outputfolder_path,
                return_mermaid_code=return_mermaid_code,
            )
        except Exception:
            error_carriers.append(carrier)
    return error_carriers


def _parse_carriers(carrier_args: list[str]) -> list[str]:
    """Parse carrier arguments from CLI into a list of carrier names.

    Accepts the following input forms:

    * Single carrier name as one argument: ``gas``
    * JSON list as one argument with quotes: ``'["gas", "coal"]'``
    * Space-separated carrier names as multiple arguments: ``gas coal electricity``
    * Comma-separated quoted strings as one argument: ``'"gas", "coal"'``

    When multiple arguments are provided, they are treated as individual carrier
    names unless the first (and only) argument is a JSON list or comma-separated
    quoted string.

    Parameters
    ----------
    carrier_args : list of str
        One or more carrier arguments supplied on the command line.

    Returns
    -------
    list of str
        One or more carrier names to process.
    """
    return carrier_args


def _process_carrier(
    carrier: str,
    n: pypsa.Network,
    bus_pattern: str | None,
    output_dir: Path,
    plot_mermaid: bool,
) -> None:
    """Build the topology for one carrier and write outputs.

    Parameters
    ----------
    carrier : str
        Carrier name to evaluate.
    n : pypsa.Network
        Loaded pypsa network.
    bus_pattern : str or None
        Optional bus name filter.
    output_dir : Path
        Directory where output files are written.
    plot_mermaid : bool
        When *True* attempt to render a PNG via mermaid.ink.
    """
    cn = CarrierNetwork(
        carrier=carrier,
        n=n,
        bus_pattern=bus_pattern,
        plot_subnetwork=False,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # Always write the Mermaid code as plain text
    mermaid_code = cn.get_mermaid_string()
    txt_path = output_dir / f"{carrier}.txt"
    txt_path.write_text(mermaid_code, encoding="utf-8")
    print(f"Mermaid code written to {txt_path}")

    if not plot_mermaid:
        return

    # Attempt to render a PNG via mermaid.ink
    try:
        cn.create_mermaid_output(
            graph=mermaid_code,
            folderpath=str(output_dir),
            return_mermaid_code=False,
        )
        print(f"PNG topology saved to {output_dir / (carrier + '.png')}")
    except Exception:
        print(
            "PNG rendering skipped. This can happen when the diagram is too large "
            "or there is no internet connection. The Mermaid code is available in "
            f"{txt_path}."
        )


def _str_to_bool(value: str) -> bool:
    """Convert a CLI string value to a boolean.

    Parameters
    ----------
    value : str
        String supplied on the command line.

    Returns
    -------
    bool
        *False* when *value* (case-insensitive) is ``"false"``, ``"0"``, or
        ``"no"``; *True* otherwise.
    """
    return value.lower() not in ("false", "0", "no")


def main() -> None:
    """Entry point for the *pypsa-topology* CLI tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Mermaid topology diagram for one or more carriers in a "
            "pypsa network. "
            "The Mermaid code is always written to resources/<carrier>.txt. "
            "A PNG render is attempted via mermaid.ink and saved as "
            "resources/<carrier>.png when the diagram is not too large. "
            "Multiple carriers can be supplied as a JSON list, e.g. "
            "'[\"gas\", \"coal\"]'."
        )
    )
    parser.add_argument(
        "path_to_pypsa_file",
        type=str,
        help="Path to the pypsa network file (.nc or .h5).",
    )
    parser.add_argument(
        "carrier",
        type=str,
        nargs="+",
        help=(
            "One or more carrier names to evaluate (must exist in the network). "
            "Can be supplied as: single name (gas), space-separated names "
            '(gas coal), or JSON list (\'["gas", "coal"]\'). '
            'When supplying names with spaces, quote each name (\\"agriculture electricity\\").'
        ),
    )
    parser.add_argument(
        "--bus-pattern",
        type=str,
        default=None,
        dest="bus_pattern",
        help=(
            "Optional substring pattern to filter buses. When provided, only "
            "buses whose name contains this pattern (and their related "
            "generators, loads, links, stores, storage units) are included. "
            "Example: --bus-pattern AT0"
        ),
    )
    parser.add_argument(
        "--plot-mermaid",
        type=_str_to_bool,
        default=True,
        dest="plot_mermaid",
        metavar="{True,False}",
        help=(
            "Whether to attempt rendering the Mermaid diagram as a PNG via "
            "mermaid.ink. Defaults to True. Pass False to skip PNG rendering "
            "and only write the Mermaid code to a .txt file."
        ),
    )
    args = parser.parse_args()

    n = pypsa.Network(args.path_to_pypsa_file)
    carriers = _parse_carriers(args.carrier)
    output_dir = Path("resources")

    for carrier in carriers:
        _process_carrier(carrier, n, args.bus_pattern, output_dir, args.plot_mermaid)


if __name__ == "__main__":
    main()


def main_component_of_carrier() -> None:
    """Entry point for the *component-of-carrier* CLI tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Show which component types in a pypsa network are attached to a "
            "given carrier.  Useful when the same carrier name is shared across "
            "multiple component types (e.g. Generator, Load, Link, Store, …)."
        )
    )
    parser.add_argument(
        "path_to_pypsa_file",
        type=str,
        help="Path to the pypsa network file (.nc or .h5).",
    )
    parser.add_argument(
        "carrier",
        type=str,
        help="Carrier name to look up (exact match).",
    )
    args = parser.parse_args()

    n = pypsa.Network(args.path_to_pypsa_file)
    result = get_components_of_carrier(n, args.carrier)

    if not result:
        print(f"No components found for carrier '{args.carrier}'.")
        return

    print(f"Carrier '{args.carrier}':")
    plural = {
        "Generator": "Generators",
        "Load": "Loads",
        "Link": "Links",
        "Line": "Lines",
        "Store": "Stores",
        "StorageUnit": "StorageUnits",
        "Bus": "Buses",
    }
    for component_type, count in result.items():
        label = plural.get(component_type, component_type + "s")
        print(f"  {label}: {count}")
