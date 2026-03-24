#!/usr/bin/env python3
"""
pypsa_network_eval – CLI and API for pypsa network topology visualisation.

Usage (command line)
--------------------
    pypsa-topology <path_to_pypsa_file> <carrier> [--bus-pattern PATTERN]

    or

    python -m energy_balance_evaluation.pypsa_network_eval <path_to_pypsa_file> <carrier>

The Mermaid code is always written to resources/<carrier>.txt relative to the
current working directory.  A PNG render is attempted and saved as
resources/<carrier>.png when the diagram is not too large.
"""

import argparse
from pathlib import Path

import pypsa

from .utils import CarriersNetwork


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


def main() -> None:
    """Entry point for the *pypsa-topology* CLI tool."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Mermaid topology diagram for a carrier in a pypsa network. "
            "The Mermaid code is always written to resources/<carrier>.txt. "
            "A PNG render is attempted via mermaid.ink and saved as "
            "resources/<carrier>.png when the diagram is not too large."
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
        help="Carrier name to evaluate (must exist in the network).",
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
    args = parser.parse_args()

    n = pypsa.Network(args.path_to_pypsa_file)

    cn = CarrierNetwork(
        carrier=args.carrier,
        n=n,
        bus_pattern=args.bus_pattern,
        plot_subnetwork=False,
    )

    output_dir = Path("resources")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Always write the Mermaid code as plain text
    mermaid_code = cn.get_mermaid_string()
    txt_path = output_dir / f"{args.carrier}.txt"
    txt_path.write_text(mermaid_code, encoding="utf-8")
    print(f"Mermaid code written to {txt_path}")

    # Attempt to render a PNG via mermaid.ink
    try:
        cn.create_mermaid_output(
            graph=mermaid_code,
            folderpath=str(output_dir),
            return_mermaid_code=False,
        )
        print(f"PNG topology saved to {output_dir / (args.carrier + '.png')}")
    except Exception:
        print(
            "PNG rendering skipped. This can happen when the diagram is too large "
            "or there is no internet connection. The Mermaid code is available in "
            f"{txt_path}."
        )


if __name__ == "__main__":
    main()
