# pypsa Network Topology Visualiser

Visualise the network topology of [pypsa](https://pypsa.org/) networks as
[Mermaid](https://mermaid.js.org/) diagrams.

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

### `pypsa-topology` – visualise carrier topology

```bash
pypsa-topology <path_to_pypsa_file> <carrier> [--bus-pattern PATTERN] [--plot-mermaid {True,False}]
```

| Argument              | Description                                                              |
|-----------------------|--------------------------------------------------------------------------|
| `path_to_pypsa_file`  | Path to the pypsa network file (`.nc` / `.h5`)                           |
| `carrier`             | Carrier name to evaluate, or a JSON list of carriers e.g. `'["gas", "coal"]'` |
| `--bus-pattern PATTERN` | *(optional)* Restrict the output to buses whose name contains *PATTERN* |
| `--plot-mermaid {True,False}` | *(optional, default `True`)* Set to `False` to skip PNG rendering and only write the Mermaid `.txt` file |

The Mermaid code is always written to `resources/<carrier>.txt`.  
A PNG render is attempted via [mermaid.ink](https://mermaid.ink) and saved as
`resources/<carrier>.png` when the diagram is not too large (unless `--plot-mermaid False` is given).

When **multiple carriers** are provided as a JSON list, each carrier is processed
independently and produces its own output files.

```bash
# Full network for carrier "gas"
pypsa-topology network.nc gas

# Only buses matching "AT0" (e.g. regional sub-set)
pypsa-topology network.nc gas --bus-pattern AT0

# Multiple carriers at once – each is processed separately
pypsa-topology network.nc '["gas", "coal"]'

# Skip PNG rendering – only produce the .txt Mermaid file
pypsa-topology network.nc gas --plot-mermaid False
```

> **Note** – The `resources/` folder is excluded from git tracking and will be
> created automatically the first time the tool runs.
- you can search for any carrier or bus_carrier in the network. 
- to limit size of network-plots, the maximum number of buses is set to 12 after a reduction of 5 in first-line buses (directly connected to carrier-element).
- Network-plots can therefore not be considered as complete for network components not directly connected to the carrier searched for.  

---

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

### `CarrierNetwork`

Evaluate and optionally visualise the sub-network for a single carrier.

```python
import pypsa
from energy_balance_evaluation import CarrierNetwork

n = pypsa.Network("my_network.nc")

# Only build the sub-network DataFrames – no plot
cn = CarrierNetwork(carrier="gas", n=n, plot_subnetwork=False)

# Get the Mermaid code as a string
print(cn.get_mermaid_string())

# Restrict to buses whose name contains "AT0"
cn = CarrierNetwork(carrier="gas", n=n, bus_pattern="AT0", plot_subnetwork=False)

# Build sub-network AND save a PNG (requires internet connection)
cn = CarrierNetwork(
    carrier="gas",
    n=n,
    png_outputfolder_path="resources",
    plot_subnetwork=True,
    return_mermaid_code=True,   # also save the .txt Mermaid code
)
```

**Parameters**

| Parameter              | Type               | Default | Description |
|------------------------|--------------------|---------|-------------|
| `carrier`              | `str`              | –       | Carrier to evaluate |
| `n`                    | `pypsa.Network`    | –       | Network to evaluate |
| `eval_one_node`        | `bool`             | `False` | Reduce to one geographical node |
| `search_therm`         | `bool \| str`      | `None`  | Node identifier for `eval_one_node` |
| `bus_pattern`          | `str \| None`      | `None`  | Optional substring to filter buses (e.g. `"AT0"`) |
| `png_outputfolder_path`| `str`              | `None`  | Output folder for PNG (required when `plot_subnetwork=True`) |
| `plot_subnetwork`      | `bool`             | `True`  | Generate and save a PNG topology plot |
| `return_mermaid_code`  | `bool`             | `False` | Also save raw Mermaid code as `.txt` |

**Attributes**

| Attribute        | Type                   | Description                         |
|------------------|------------------------|-------------------------------------|
| `carrier`        | `str`                  | Carrier name                        |
| `n`              | `pypsa.Network`        | The evaluated network               |
| `generators`     | `pandas.DataFrame`     | Generators of the carrier           |
| `buses`          | `pandas.DataFrame`     | Buses of the carrier                |
| `links`          | `pandas.DataFrame`     | Links connected to the carrier buses|
| `lines`          | `pandas.DataFrame`     | Lines connected to the carrier buses|
| `stores`         | `pandas.DataFrame`     | Stores of the carrier               |
| `storage_units`  | `pandas.DataFrame`     | Storage units of the carrier        |
| `loads`          | `pandas.DataFrame`     | Loads of the carrier                |
| `processes`      | `numpy.ndarray`        | Carrier labels of links and lines   |

---

### `CarriersNetwork`

Base class used by `CarrierNetwork`.  Can be used directly when the PNG
rendering step is not needed.

```python
from energy_balance_evaluation import CarriersNetwork

cn = CarriersNetwork(carrier="gas", n=n)
mermaid_code = cn.get_mermaid_string()

# Filter to a specific region
cn_at0 = CarriersNetwork(carrier="gas", n=n, bus_pattern="AT0")
```

---

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

### `eval_all_networks`

Evaluate all carriers in a network and save topology plots.

```python
from energy_balance_evaluation import eval_all_networks

failed = eval_all_networks(
    n,
    png_outputfolder_path="resources",
    eval_one_node=True,
    return_mermaid_code=True,
)
print("Failed carriers:", failed)
```

---

## Network Topology diagram

The topology diagram shows:

- **Buses** (triple circles `((( )))`) – the carrier's main buses
- **Generators** (rectangles `[ ]`) – connected to their bus with a thick edge (`===`)
- **Loads** (rounded rectangles `( )`) – connected to their bus with a thick edge
- **Storage units** – connected to their bus with a thick edge
- **Links** – shown as labelled directed edges (`-- label -->`)
  - Multi-link bus2,3,4 - connections are marked *indirect*
- **Lines** – shown as labelled directed edges

> [!NOTE]
> When the Mermaid code is too large for the URI-based rendering API, the
> raw code is saved to a `.txt` file for manual rendering.

![methanol_small](https://github.com/user-attachments/assets/70a3239c-5d6c-4ffd-9c80-6e852fe54f53)

## Limitations
- The package gives a complete overview of buses, generators, loads, storage_units, links and lines with respect to the given carrier. 
- This implies, that buses and other elements, not directly connected to the "main" bus, holding the given carrier, are only shown in relation to the given carrier. 

> In the given example, this means, that there are probably more links connected to the bus "co2 atmosphere" than shown in this plot, but they are not directly related to the main carrier "methanol" in here.

- Depending on the network-topology, plots can get very large and hard to understand. This is expecially given for carriers modeled on a single bus, as EU oil, EU methanol, EU gas, etc. Therefore use the `--bus-pattern` to filter buses. 
- The package is still under development, so expect ongoing changes.
