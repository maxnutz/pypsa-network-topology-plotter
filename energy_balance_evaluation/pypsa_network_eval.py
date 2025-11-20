#!/usr/bin/env python3

import pypsa
import pandas as pd
import numpy as np
import os

from .utils import CarriersNetwork


class CarrierNetwork(CarriersNetwork):
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
            if png_outputfolder_path == None:
                raise Exception(
                    "When plotting subnetworks, you have to provide an outputfolder (png_outputfolder_path)"
                )
            else:
                self.plot_subnetwork(png_outputfolder_path, return_mermaid_code)

        def __repr__(self):
            cls = self.__class__.__name__
            vars = " -- access variables: generators, buses, links, lines, stores, storage_units, loads, processes, relevant for given carrier."
            return f"CarrierNetwork(carrier={self.carrier})" + vars


def eval_all_networks(
    n: pypsa.Network,
    png_outputfolder_path: str,
    eval_one_node: bool = True,
    return_mermaid_code: bool = False,
):
    """
    Evaluates all carriers in a given pypsa.Network object.

    Parameters:
    ---
    n : pypsa.Network
        The network object to be evaluated.
    png_outputfolder_path : str
        The path where the subnetwork plots should be saved.
    eval_one_node : bool, optional
        Whether to reduce the network to one node. Defaults to True.
    return_mermaid_code : bool, optional
        Whether to return the mermaid code as text. Defaults to False.

    Returns:
    ---
    error_carriers : list
        A list of carriers for which the evaluation failed.
    """
    error_carriers = []
    for carrier in n.carriers.index.values:
        if carrier == "none" or carrier == "" or carrier == " ":
            pass
        else:
            try:
                CarrierClass = CarrierNetwork(
                    carrier,
                    n,
                    eval_one_node=eval_one_node,
                    png_outputfolder_path=png_outputfolder_path,
                    return_mermaid_code=return_mermaid_code,
                )
            except:
                error_carriers.append(carrier)
    return error_carriers


def main():
    import pypsa

    filepath = "/home/max/Dokumente/BOKU/scripting/nora_outputs/AT-all_sectors-07_05_02CO2-wj1942-overnight-1y/networks/base_s_5__Co2L0.2_2030-1942.nc"
    n = pypsa.Network(filepath)
    error_carriers_at = []
    for carrier in n.carriers.index.values:
        if carrier == "none" or carrier == "" or carrier == " ":
            pass
        else:
            CarrierClass = CarrierNetwork(
                carrier,
                n,
                eval_one_node=True,
                png_outputfolder_path="/home/max/Dokumente/BOKU/infra-enshure/pypsa_network_eval/test_plots",
            )


if __name__ == "__main__":
    main()
