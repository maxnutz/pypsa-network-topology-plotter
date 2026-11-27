# Specification: interactive carrier topology (HTML)

Replaces the Mermaid/PNG output (incl. mermaid.ink calls and the 7/5/12 bus caps) entirely.

## CLI

```
pypsa-topology <network.nc> <carrier>... [--region R] [--depth N] [--output-dir DIR]
```

- `carrier` matches `bus.carrier` **exactly**. No match → error listing similar existing carriers. Multiple carriers → one HTML per carrier.
- `--region R` (optional): if any `bus.location == R`, match buses by location; otherwise fall back to substring match on the bus name.
- `--depth N` (default 1): number of bus hops expanded from the start buses over links, lines and transformers.
- Output: `<output-dir>/<carrier>[_<region>].html`, default output dir `resources/`.
- `component-of-carrier` CLI stays unchanged.

## Element selection

1. **Start buses**: all buses with `carrier == <carrier>`; if `--region` is given, only those in the region.
2. **Expansion**: from the start buses, follow every link (all ports `bus0..busN`), line and transformer touching them, `N` hops.
3. **Attached elements**: every generator, load, store and storage unit connected to an included bus.

## View without region: aggregated by carrier

- **Do not draw every bus of the carrier.** All start buses (e.g. all 51 `* H2` buses) collapse into **one** node `H2`.
- Every other included bus is likewise collapsed into one node per bus carrier (one `AC`, one `gas`, one `co2 stored`, …).
- Links are grouped by link carrier. The `H2` node shows the **union** of all link types found at any regional H2 bus: if `AT11 H2` has Electrolysis but no SMR and `AT12 H2` has SMR but no Electrolysis, both appear.
- Links between buses of the same carrier (e.g. `H2 pipeline`) are drawn as a self-loop on that carrier node.
- Generators/loads/stores/storage units are aggregated per (bus carrier, component carrier).

## View with region: fully detailed

- Every bus is its own node, including the buses in other regions at the far end of links (cross-region structure stays visible).
- Every element connected to the region's carrier bus(es) is drawn individually.
- Exception: branches that are identical in component, carrier, `bus0` and every `(port, bus, efficiency)` (e.g. build-year vintages `…-2010`, `…-2015`) are merged into one (multi)link; the label shows `(n=X)`, the tooltip lists the members and the summed capacity. Branches that differ in any efficiency stay separate.

## Drawing rules

- Every link is drawn as one line per port: `bus0→bus1`, `bus0→bus2`, … `bus0→busN`.
- All lines of one (multi)link share one colour and a group label (link name / link carrier), so they read as one multilink.
- Arrows always point `bus0 → busN` (pypsa port order). Each line is labelled with its efficiency **including sign** (e.g. `η2=-0.25`).
- Node colours from `n.carriers.color` where set, fixed palette otherwise.

## Interaction (HTML via pyvis / vis-network)

- Hovering an element highlights it and all connected elements; hovering a line of a multilink highlights all its lines and buses.
- In the aggregated view, the tooltip lists how many individual components are behind a node/edge, and which ones.

## Test network

`/home/mnutz/projects/pypsa-at/results/main-sensitivities/AT_KN2040/networks/solved_2025.nc`
(pypsa 1.4; 1758 buses, 7242 links, 98 lines, 51 `H2` buses with `location` e.g. `AT11`; links have ports `bus0..bus4`, many negative `efficiency2..4`).
