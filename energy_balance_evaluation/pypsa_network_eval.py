#!/usr/bin/env python3
"""
pypsa_network_eval – CLI and API for pypsa network topology visualisation.

Usage (command line)
--------------------
    pypsa-topology <path_to_pypsa_file> <carrier>

    or

    python -m energy_balance_evaluation.pypsa_network_eval <path_to_pypsa_file> <carrier>

The Mermaid code is written to resources/<carrier>.txt relative to the
current working directory.
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
        png_outputfolder_path: str = None,
        plot_subnetwork: bool = True,
        return_mermaid_code: bool = False,
    ):
        super().__init__(carrier, n, eval_one_node, search_therm)
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
            "Generate Mermaid topology code for a carrier in a pypsa network "
            "and write it to resources/<carrier>.txt."
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
    args = parser.parse_args()

    n = pypsa.Network(args.path_to_pypsa_file)

    cn = CarrierNetwork(
        carrier=args.carrier,
        n=n,
        plot_subnetwork=False,
    )
    mermaid_code = cn.get_mermaid_string()

    output_path = Path("resources") / f"{args.carrier}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mermaid_code, encoding="utf-8")
    print(f"Mermaid code written to {output_path}")


if __name__ == "__main__":
    main()
