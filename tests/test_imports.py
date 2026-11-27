"""
Tests for package imports and module structure.
"""

import energy_balance_evaluation as pkg


def test_all_exports() -> None:
    for name in pkg.__all__:
        assert hasattr(pkg, name), f"Missing export: {name}"
    assert {"CarrierTopology", "plot_carrier_topology", "InputError"} <= set(
        pkg.__all__
    )
