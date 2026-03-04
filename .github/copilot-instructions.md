---
applyTo: "**/*.py, **/*.yaml"
---

# Project Overview 
> [!NOTE]
> This is an AGENT.md - file for AI agents, specifically for Copilot in this case. It is used to provide instructions to the AI agent on how to interact with project and developers.

## Aim of the project
- Create a consistent set of well-designed variables to be used for Energy Data Validation
- use the nomenclature-package and the pyam-package to implement a validation process for outputs of an Energy System Model and provide a technically processable output of this validation-process.
- use consistent and generally applicable variables and definitions in the IAMC-Format

## Folder Structure
- `energy_balance_evaluation`: Contains the package code for evaluating the Eurostat Energy Balance data and for evaluation of pypsa-at/pypsa-de/pypsa-eur networks 
- `definitions`: Contains the variable-definition in IAMC-format following the structure of the `nomenclature` package. 
- `resources`: input-resources for processing
    - `eurostat_nrg_present.csv`: nrg-Definition of Eurostat variables
    - `eurostat_siec_present.csv`: siec-Definition of Eurostat variables
    - `adriane_variables.yaml`: a set of variables to be used as basis for the definitions/variable/variables.yaml - variables.
- `tests`: package testing code.

## Operating rules (Mandatory)
- Prefer modifying existing modules over creating new files.
- Only create new files if no logical location exists.
- Never duplicate functionality already present in the package.
- Give a short overview of what you created afterwards in the chat.
- Before writing code, ask at least two clarification questions IF any of the following apply:
    - requirements are ambiguous
    - input/output format is unclear
    - multiple architectural choices exist
    - required files are missing or unclear

## Coding conventions
- Use type hints for all functions.
- Add docstrings in NumPy-style format
- Use pyam / pandas idioms instead of manual loops wherever possible 


## Task Completion Criteria
A task is complete when:
- Code runs without syntax errors.
- Tests pass or new tests are added and pass.
- New variables follow IAMC naming conventions.
- Changes are integrated into existing folder structure.
- A short summary of changes is provided.
- In chat mode: the user has reviewed the changes and gave approval.

## Forbidden Actions

- Do NOT invent datasets, files, or APIs.
- Do NOT assume undocumented variables exist.
- Do NOT change any definitions in `definitions/` unless explicitly asked for.
- Do NOT change folder structure unless explicitly requested.

## Testing Rules
- Add or update tests when behavior changes.
- Tests belong only in `/tests`.
- Prefer minimal unit tests over integration tests.

---

## Background information on important packages and data
> [!WARNING]
> External documentation provides semantic guidance only. Local project conventions override external documentation.
- nomenclature-package: https://nomenclature-iamc.readthedocs.io/en/stable/
- pyam-package: https://pyam-iamc.readthedocs.io/en/stable/
- IAMC-format naming conventions: https://docs.ece.iiasa.ac.at/standards/variables.html
- Documentation of the Eurostat energy balance: https://ec.europa.eu/eurostat/documents/38154/4956218/ENERGY-BALANCE-GUIDE.pdf/de76d0d2-8b17-b47c-f6f5-415bd09b7750?t=1632139948586

