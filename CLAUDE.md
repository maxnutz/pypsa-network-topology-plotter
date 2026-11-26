# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python package (`energy_balance_evaluation`) that writes an interactive HTML plot (pyvis / vis-network) of the topology of a [pypsa](https://pypsa.org/) network around a bus carrier. The plot focuses on sector-coupling links and on connections between regions. The agreed requirements are in `SPEC.md`; keep the code and that file consistent.

## Commands

Run everything through the pixi environment (this is also what CI does):

```bash
pixi run pytest                                              # full test suite (CI: .github/workflows/tests.yml)
pixi run pytest tests/test_graph.py                          # one file
pixi run pytest tests/test_graph.py::TestRegionView::test_location_match   # one test
black energy_balance_evaluation tests                        # formatter (pre-commit hook; black is not in the pixi env)
pixi run pypsa-topology network.nc H2 --region AT11 --depth 1 --output-dir resources
pixi run component-of-carrier network.nc gas
```

A real network for manual checks: `/home/mnutz/projects/pypsa-at/results/main-sensitivities/AT_KN2040/networks/solved_2025.nc`. It has 51 `H2` buses with `location` values such as `AT11`.

## Architecture

The pipeline has two stages: selection and graph building in `graph.py`, then rendering in `html_export.py`. The graph is independent of plotting, so selection logic is tested without HTML.

- `graph.py`:
  - `branch_ports(n)` flattens links, lines and transformers into one long table with one row per port (`bus0 → bus<port>`), including the signed `efficiency<port>`.
  - `CarrierTopology` finds the start buses. The carrier is an **exact** match on `bus.carrier`. If `--region` equals some `bus.location`, buses are matched by location; otherwise by substring of the bus name.
  - It then expands `depth` bus hops. A branch is always selected **as a whole** (all of its ports) once any of its buses is included.
  - It then attaches the one-port components on every included bus.
  - `build_graph()` produces a `TopologyGraph` of `Node` and `Edge` objects. Without a region it is **aggregated**: node id `bus|<bus carrier>`, and edges grouped by (component, carrier, port, source, target). With a region it is **detailed**: node id `bus|<bus name>`, one edge per port.
  - `Edge.group` ties together all lines of one multilink: `Link|<name>` in the detailed view, `Link|<carrier>` in the aggregated view.
- `html_export.py`:
  - Converts the graph to pyvis and writes the HTML with vis-network inlined (`cdn_resources="in_line"`).
  - Each edge carries a custom `linkgroup` attribute taken from `Edge.group`.
  - Parallel edges get curved `smooth` settings and self-loops get sized `selfReference` settings so they don't overlap.
  - After pyvis renders, it injects CSS (multi-line tooltips), a header, and `_HIGHLIGHT_JS`. That script relies on pyvis's global `network`, `nodes` and `edges` variables and must run after `drawGraph();`.
- `pypsa_network_eval.py`: holds `plot_carrier_topology`, `eval_all_networks` and both CLI entry points. `_parse_carriers` normalizes the `carrier` (`nargs="+"`) input forms; `tests/test_cli.py::TestParseCarriers` covers them.
- `utils.py`: `InputError` and `get_components_of_carrier`, which uses exact carrier equality.

The Mermaid/PNG output and its bus caps were removed on purpose. Arrows always follow pypsa port order `bus0 → busN`; the efficiency sign in the label shows the real direction.

## Tests

- Tests build small in-memory networks. The `two_region_network` fixture in `tests/conftest.py` has Electrolysis only in R1, SMR (with negative `efficiency2`) only in R2, and an H2 pipeline between them. It covers the union-across-regions, self-loop, multilink and region-matching cases.
- HTML tests parse the `nodes`/`edges` `vis.DataSet` JSON out of the generated page.

## Project rules (from `.github/copilot-instructions.md`)

- Use type hints on all functions and NumPy-style docstrings. Prefer pandas idioms over manual loops.
- Modify existing modules rather than adding new files. Don't duplicate existing functionality.
- Do not edit `definitions/` (IAMC/nomenclature variable YAMLs) unless explicitly asked. New variables follow IAMC naming conventions.
- Do not change the folder structure unless asked. Never modify `sister_packages/` if present.
- Ask clarifying questions before coding when requirements, I/O formats or architectural choices are ambiguous.
- Add or update tests in `tests/` when behavior changes. Prefer minimal unit tests.
