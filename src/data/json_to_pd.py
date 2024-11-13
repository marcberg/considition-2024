import pandas as pd
import json

def load_game_rules_to_df(file_path="data/Map-Almhult.json"):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    games_rules = []
    games_rules_entry = {
        "name": data["name"],
        "budget": data["budget"],
        "gameLengthInMonths": data["gameLengthInMonths"],
    }
    games_rules.append(games_rules_entry)

    return pd.DataFrame(games_rules)

def load_map_to_df(file_path=r"data/Map-Almhult.json"):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        data = json.load(file)

    customers_data = []
    for customer in data["customers"]:
        customer_entry = {
            "name": customer["name"],
            "loan_product": customer["loan"]["product"],
            "environmentalImpact": customer["loan"]["environmentalImpact"],
            "loan_amount": customer["loan"]["amount"],
            "personality": customer["personality"],
            "capital": customer["capital"],
            "income": customer["income"],
            "monthlyExpenses": customer["monthlyExpenses"],
            "numberOfKids": customer["numberOfKids"],
            "homeMortgage": customer["mortgage"],
            "hasStudentLoan": customer["hasStudentLoans"]
        }
        customers_data.append(customer_entry)

    return pd.DataFrame(customers_data)
