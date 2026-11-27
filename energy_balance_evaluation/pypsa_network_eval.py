#!/usr/bin/env python3
"""
pypsa_network_eval – CLI and API for interactive pypsa topology plots.

Usage (command line)
--------------------
    pypsa-topology <path_to_pypsa_file> <carrier>... [--region REGION]
                   [--depth N] [--output-dir DIR]

Without ``--region`` all buses of the carrier are merged into one node (and
all other buses into one node per carrier). With ``--region`` every bus and
component connected to the region's carrier bus(es) is drawn individually.

The output is written to ``<output-dir>/<carrier>[_<region>].html``
(default output dir: ``resources``).
"""

import argparse
import json
import sys
from pathlib import Path

import pypsa

from .graph import CarrierTopology
from .html_export import output_filename, write_topology_html
from .utils import InputError, get_components_of_carrier


def plot_carrier_topology(
    n: pypsa.Network,
    carrier: str,
    region: str | None = None,
    depth: int = 1,
    output_dir: str | Path = "resources",
) -> Path:
    """Build the topology around *carrier* and write it as interactive HTML.

    Parameters
    ----------
    n : pypsa.Network
        The network to evaluate.
    carrier : str
        Bus carrier to start from (exact match).
    region : str or None, optional
        Optional region (``bus.location`` or substring of the bus name).
        Without a region, the graph is aggregated by carrier.
    depth : int, optional
        Number of bus hops expanded from the carrier bus(es). Defaults to 1.
    output_dir : str or pathlib.Path, optional
        Output folder. Defaults to ``"resources"``.

    Returns
    -------
    pathlib.Path
        Path of the written HTML file.

    Raises
    ------
    InputError
        When the carrier or region is not found.
    """
    graph = CarrierTopology(n, carrier, region=region, depth=depth).build_graph()
    return write_topology_html(
        graph, Path(output_dir) / output_filename(carrier, region)
    )


def eval_all_networks(
    n: pypsa.Network,
    output_dir: str | Path = "resources",
    depth: int = 1,
) -> list[str]:
    """Write an aggregated topology HTML for every bus carrier of *n*.

    Parameters
    ----------
    n : pypsa.Network
        The network to evaluate.
    output_dir : str or pathlib.Path, optional
        Output folder. Defaults to ``"resources"``.
    depth : int, optional
        Number of bus hops. Defaults to 1.

    Returns
    -------
    list of str
        Carriers that could not be processed.

    Notes
    -----
    Buses without a meaningful carrier (empty, whitespace or ``"none"``) are
    skipped.
    """
    carriers = n.buses["carrier"].dropna().astype(str)
    stripped = carriers.str.strip()
    carriers = carriers[(stripped != "") & (stripped.str.lower() != "none")]
    failed = []
    for carrier in carriers.unique():
        try:
            plot_carrier_topology(n, carrier, depth=depth, output_dir=output_dir)
        except Exception as exc:  # keep going for the remaining carriers
            print(f"Carrier '{carrier}' failed: {exc}")
            failed.append(carrier)
    return failed


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
    # Multiple plain carriers passed as separate positional args (e.g. gas coal)
    if len(carrier_args) > 1:
        return list(carrier_args)

    arg = carrier_args[0].strip()

    # JSON list form: '["gas", "coal"]' or ["gas", "coal"] (with or without outer quotes)
    if arg.startswith("["):
        try:
            parsed = json.loads(arg)
            if isinstance(parsed, list) and all(isinstance(c, str) for c in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

    # Comma-separated quoted strings without brackets: '"gas", "coal"'
    try:
        parsed = json.loads(f"[{arg}]")
        if (
            isinstance(parsed, list)
            and len(parsed) > 1
            and all(isinstance(c, str) for c in parsed)
        ):
            return parsed
    except json.JSONDecodeError:
        pass

    # Single carrier (plain string or unrecognised form)
    return list(carrier_args)


def main() -> None:
    """Entry point for the *pypsa-topology* CLI tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Write an interactive HTML topology plot around one or more "
            "carriers of a pypsa network to <output-dir>/<carrier>[_<region>].html."
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
            "One or more bus carriers (exact match). Can be supplied as: single "
            "name (H2), space-separated names (H2 gas), or JSON list "
            '(\'["H2", "gas"]\'). Quote names containing spaces.'
        ),
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help=(
            "Optional region. Matched exactly against bus.location if any bus "
            "has that location, otherwise as substring of the bus name. Without "
            "a region all buses of a carrier are merged into one node."
        ),
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Number of bus hops expanded from the carrier bus(es). Default: 1.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="resources",
        dest="output_dir",
        help="Output folder for the HTML files. Default: resources.",
    )
    args = parser.parse_args()

    n = pypsa.Network(args.path_to_pypsa_file)
    failed = False
    for carrier in _parse_carriers(args.carrier):
        try:
            path = plot_carrier_topology(
                n,
                carrier,
                region=args.region,
                depth=args.depth,
                output_dir=args.output_dir,
            )
        except InputError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            failed = True
            continue
        print(f"Topology written to {path}")
    if failed:
        sys.exit(1)


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


if __name__ == "__main__":
    main()
