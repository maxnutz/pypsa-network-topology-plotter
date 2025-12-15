# dict of rows to include for the light version of the energy balance
rows_to_include_dict = {
    "Total_absolute_values": {
        "Primary_production": True,
        "Recovered_and_recycled_products": False,
        "Imports": True,
        "Exports": True,
        "Change_in_stock": True,
        "Gross_available_energy": True,
        "International_maritime_bunkers": True,
        "Gross_inland_consumption": True,
        "International_aviation": True,
        "Total_energy_supply": True,
        "Gross_inland_consumption_(Europe_2020-2030)": False,
        "Primary_energy_consumption_(Europe_2020-2030)": False,
        "Final_energy_consumption_(Europe_2020-2030)": False,
    },
    "Transformation_input": {
        "nan": True,
        "Electricity_and_heat_generation": {
            "nan": True,
            "Main_activity_producer_electricity_only": True,
            "Main_activity_producer_CHP": True,
            "Main_activity_producer_heat_only": True,
            "Autoproducer_electricity_only": True,
            "Autoproducer_CHP_": True,
            "Autoproducer_heat_only": True,
            "Electrically_driven_heat_pumps": True,
            "Electric_boilers": False,
            "Electricity_for_pumped_storage": True,
            "Derived_heat_for_electricity_production": False,
        },
        "Coke_ovens": False,
        "Blast_furnaces": False,
        "Gas_works": True,
        "Refineries_and_petrochemical_industry": {
            "nan": True,
            "Refinery_intake": False,
            "Backflows_from_petrochemical_industry": False,
            "Products_transferred": False,
            "Interproduct_transfers": False,
            "Direct_use": False,
            "Petrochemical_industry_intake": False,
        },
        "Patent_fuel_plants": False,
        "BKB_and_PB_plants": False,
        "Coal_liquefaction_plants": False,
        "For_blended_natural_gas": False,
        "Liquid_biofuels_blended": False,
        "Charcoal_production_plants": False,
        "Gas-to-liquids_plants": False,
        "Not_elsewhere_specified_": False,
    },
    "Transformation_output": False,
    "Energy_sector": False,
    "Distribution_losses": True,
    "Available_for_final_consumption": True,
    "Final_non-energy_consumption": False,
    "Final_energy_consumption": {
        "nan": True,
        "Industry_sector": {
            "nan": True,
            "Iron_and_steel": False,
            "Chemical_and_petrochemical": False,
            "Non-ferrous_metals": False,
            "Non-metallic_minerals": False,
            "Transport_equipment": False,
            "Machinery": False,
            "Mining_and_quarrying": False,
            "Food_beverages_and_tobacco": False,
            "Paper_pulp_and_printing": False,
            "Wood_and_wood_products": False,
            "Construction": False,
            "Textile_and_leather": False,
            "Not_elsewhere_specified_(industry)": False,
        },
        "Transport_sector": {
            "nan": True,
            "Rail": True,
            "Road": True,
            "Domestic_aviation": True,
            "Domestic_navigation": True,
            "Pipeline_transport": True,
            "Not_elsewhere_specified_(transport)": False,
        },
        "Other_sectors": {
            "nan": True,
            "Commercial_and_public_services": True,
            "Households": True,
            "Agriculture_and_forestry": True,
            "Fishing": True,
            "Not_elsewhere_specified_(other)": False,
        },
    },
}


# dict of rows-lists to be added together for the light version of the energy balance
rows_to_add_dict = {
    "Final_energy_consumption>Transport_sector>Land_transport": [
        "Final_energy_consumption>Transport_sector>Road",
        "Final_energy_consumption>Transport_sector>Rail",
        "Final_energy_consumption>Transport_sector>Domestic_navigation",
    ],
    "Total_absolute_values>National_and_International_aviation": [
        "Total_absolute_values>International_aviation",
        "Final_energy_consumption>Transport_sector>Domestic_aviation",
    ],
    "Final_energy_consumption>Other_sectors>Households_and_Commercial_and_public_services": [
        "Final_energy_consumption>Other_sectors>Commercial_and_public_services",
        "Final_energy_consumption>Other_sectors>Households",
    ],
    "Final_energy_consumption>Other_sectors>Agriculture_and_forestry_and_fishing": [
        "Final_energy_consumption>Other_sectors>Agriculture_and_forestry",
        "Final_energy_consumption>Other_sectors>Fishing",
    ],
}


# dict of string elements to be replaced when creating light energy balance names
eb_row_string_replacement_dict = {" ": "_", ",": "_", "&": "and", "/": "_"}

# non numerical columns in eurostat energy balance matrix
non_numerical_columns_list = [
    "layer_0",
    "layer_1",
    "layer_2",
    "index",
    "+/-",
    "depth",
    "var_name",
]
