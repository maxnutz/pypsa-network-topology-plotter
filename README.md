# pypsa Network Topology Visualiser

Interactive HTML plots of the topology of a [pypsa](https://pypsa.org/)
network around a carrier, focused on sector-coupling links and the
connections between regions.

---

## Installation
Install directly from GitHub
```bash
pip install git+https://github.com/maxnutz/pypsa-network-topology-plotter
```
Or clone locally and install with
```bash
pip install .
```

---


## CLI usage

After installation two CLI commands are available:

### `pypsa-topology` – interactive topology around a carrier

```bash
pypsa-topology <path_to_pypsa_file> <carrier>... [--region REGION] [--depth N] [--output-dir DIR]
```

| Argument | Description |
|----------|-------------|
| `path_to_pypsa_file` | Path to the pypsa network file (`.nc` / `.h5`) |
| `carrier` | One or more **bus** carriers (exact match), e.g. `H2`, `H2 gas`, or `'["H2", "gas"]'` |
| `--region REGION` | *(optional)* Matched exactly against `bus.location` if any bus has that location, otherwise as a substring of the bus name |
| `--depth N` | *(optional, default 1)* Number of bus hops expanded from the carrier bus(es) |
| `--output-dir DIR` | *(optional, default `resources`)* Output folder |

Each carrier is written to `<output-dir>/<carrier>[_<region>].html`, a single
self-contained file (vis-network is inlined, so it opens offline).

```bash
# All H2 buses merged into one H2 node, with every link type found at any H2 bus
pypsa-topology network.nc H2

# Everything connected to the H2 bus of location AT11, every bus drawn individually
pypsa-topology network.nc H2 --region AT11

# "AT" is no location -> substring match: the H2 buses of all Austrian regions
pypsa-topology network.nc H2 --region AT

# Two hops out from the H2 buses
pypsa-topology network.nc H2 --depth 2
```

If the carrier is not found, the tool suggests similar bus carriers.

### What is drawn

Starting from the buses of the carrier (within the region, if given), every
link (all ports `bus0…busN`), line and transformer touching an included bus
is followed for `--depth` hops. Generators, loads, stores and storage units
on all included buses are added.

- **Without region – aggregated view.** All buses of a carrier collapse into
  one node (one `H2`, one `AC`, one `gas`, …). Links are grouped by link
  carrier, so the `H2` node shows the union of all link types of all regions
  (e.g. Electrolysis from one region and SMR from another). Links between
  buses of the same carrier (e.g. `H2 pipeline`) are drawn as a self-loop.
  Labels and tooltips show how many components are behind each node/edge.
- **With region – detailed view.** Every bus and component is drawn
  individually, including the buses in other regions at the far end of links.

Drawing rules:

- A link is drawn as one line per port (`bus0→bus1`, `bus0→bus2`, …). All
  lines of one (multi)link share colour and label.
- Arrows always point `bus0 → busN`; labels show the efficiency of the port
  **with sign** (`η2=-0.2` means bus2 is an input).
- Shapes: ● bus, ▲ generator, ▼ load, ■ store, ◆ storage unit. Colours come
  from `n.carriers.color` where set.
- Hovering a node or line highlights it together with all lines of the
  (multi)links involved and the connected buses; tooltips list the members.
  The layout settles once and can then be dragged and zoomed.

### `component-of-carrier` – find which components use a carrier

When the same carrier name is used by different component types in a network
(e.g. a `Generator` *and* a `Link` both carry `"gas"`), this command shows
all component types that are attached to the given carrier:

```bash
component-of-carrier <path_to_pypsa_file> <carrier>
```

| Argument             | Description                                      |
|----------------------|--------------------------------------------------|
| `path_to_pypsa_file` | Path to the pypsa network file (`.nc` / `.h5`)   |
| `carrier`            | Carrier name to look up (exact match)            |

Example output:

```
Carrier 'gas':
  Generators: 2
  Loads: 1
  Links: 1
  Buses: 2
```

---


## Python API

```python
import pypsa
from energy_balance_evaluation import CarrierTopology, plot_carrier_topology, write_topology_html

n = pypsa.Network("my_network.nc")

# One call: build and write resources/H2_AT11.html
path = plot_carrier_topology(n, "H2", region="AT11", depth=1, output_dir="resources")

# Or step by step
topo = CarrierTopology(n, "H2")          # selection: start_buses, buses, ports, one_ports
graph = topo.build_graph()              # plot-independent TopologyGraph (nodes, edges)
write_topology_html(graph, "resources/H2.html")
```

`eval_all_networks(n, output_dir="resources")` writes an aggregated plot for
every bus carrier (skipping empty and `"none"` carriers) and returns the
carriers that failed.

### `get_components_of_carrier`

Find out how many components of each type in a network use a given carrier name.

```python
import pypsa
from energy_balance_evaluation import get_components_of_carrier

n = pypsa.Network("my_network.nc")

result = get_components_of_carrier(n, "gas")
# e.g. {'Generator': 2, 'Link': 1, 'Bus': 2}

for component_type, count in result.items():
    print(f"{component_type}s: {count}")
```

Returns a `dict` mapping component type names to the **count** of matching
components.  Component types with no match for the carrier are omitted.

---


## Limitations

- Efficiencies are the static `efficiency…` attributes; time-varying
  efficiencies are ignored.
- In the aggregated view, hub carriers such as `AC` attach all their
  generators and loads (aggregated by carrier). With `--depth 2` or more the
  graph can grow quickly.
