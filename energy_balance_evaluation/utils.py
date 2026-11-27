"""
utils – shared helpers: :class:`InputError` and :func:`get_components_of_carrier`.
"""

import pypsa


class InputError(Exception):
    """Raised when the requested carrier or region is not found in the network."""

    pass


def get_components_of_carrier(n: pypsa.Network, carrier: str) -> dict:
    """
    Return the count of network components attached to *carrier* per type.

    Checks all one-port and branch component types for membership of the
    given carrier and returns a mapping from component type name to the
    number of components carrying that carrier.

    Parameters
    ----------
    n : pypsa.Network
        The network to inspect.
    carrier : str
        The carrier name to look up (exact match against the ``carrier``
        column of each component DataFrame).

    Returns
    -------
    dict of {str: int}
        Keys are component type names (e.g. ``"Generator"``, ``"Load"``,
        ``"Link"``, ``"Line"``, ``"Store"``, ``"StorageUnit"``, ``"Bus"``).
        Values are the number of components whose carrier equals *carrier*.
        Component types with no match are omitted from the result.

    Examples
    --------
    >>> import pypsa
    >>> n = pypsa.Network()
    >>> n.add("Carrier", "gas")
    >>> n.add("Bus", "bus_gas", carrier="gas")
    >>> n.add("Generator", "gen_gas", bus="bus_gas", carrier="gas", p_nom=100)
    >>> get_components_of_carrier(n, "gas")
    {'Generator': 1, 'Bus': 1}
    """
    component_dfs = {
        "Generator": n.generators,
        "Load": n.loads,
        "Link": n.links,
        "Line": n.lines,
        "Store": n.stores,
        "StorageUnit": n.storage_units,
        "Bus": n.buses,
    }
    result = {}
    for component_type, df in component_dfs.items():
        if "carrier" not in df.columns or df.empty:
            continue
        count = int((df["carrier"] == carrier).sum())
        if count > 0:
            result[component_type] = count
    return result
