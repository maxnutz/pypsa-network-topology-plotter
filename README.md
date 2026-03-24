# pypsa Network Topology Visualiser

Visualise the network topology of [pypsa](https://pypsa.org/) networks as
[Mermaid](https://mermaid.js.org/) diagrams.

---

## Installation

```bash
pip install .
```

---

## CLI usage

After installation the `pypsa-topology` command is available:

```bash
pypsa-topology <path_to_pypsa_file> <carrier>
```

| Argument            | Description                                    |
|---------------------|------------------------------------------------|
| `path_to_pypsa_file`| Path to the pypsa network file (`.nc` / `.h5`) |
| `carrier`           | Carrier name to evaluate                       |

The Mermaid code is written to `resources/<carrier>.txt` relative to the
current working directory.

> **Note** – The `resources/` folder is excluded from git tracking and will be
> created automatically the first time the tool runs.

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
```

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
  - Multi-link bus2 connections are marked *indirect*
- **Lines** – shown as labelled directed edges

> When the Mermaid code is too large for the URI-based rendering API, the
> raw code is saved to a `.txt` file for manual rendering.

![methanol_small](https://github.com/user-attachments/assets/70a3239c-5d6c-4ffd-9c80-6e852fe54f53)
