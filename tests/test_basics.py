import yaml
import pandas as pd
from energy_balance_evaluation import VariablesSet


def test_import_variables_set():
    assert VariablesSet is not None


def test_read_yaml_file(tmp_path):
    yaml_content = [
        {"Final Energy": {"nrg": "FC_E", "siec": "TOTAL"}}
    ]
    p = tmp_path / "vars.yaml"
    p.write_text(yaml.safe_dump(yaml_content))
    vs = VariablesSet("final_energy", 2020, str(p), "out.yaml", country="AT")
    d = vs.read_yaml_file()
    assert "Final Energy" in d


def test_calculate_variable_values_with_dataframe():
    vs = VariablesSet(
        "final_energy",
        2020,
        "definitions/variable/final_energy.yaml",
        "out.yaml",
        country="AT",
    )
    vs.variables_dict = {"Final Energy": {"nrg": "FC_E", "siec": "TOTAL"}}
    df = pd.DataFrame(
        [
            {
                "freq": "A",
                "nrg_bal": "FC_E",
                "siec": "TOTAL",
                "unit": "GWH",
                "geo": "AT",
                "2020": 100.0,
            }
        ]
    )
    vs.tsv_data = df
    res = vs.calculate_variable_values("unused.tsv")
    assert res["Final Energy"] == 100.0
