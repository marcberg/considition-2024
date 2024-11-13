import pandas as pd
import os

from src.data.json_to_pd import load_game_rules_to_df, load_map_to_df


def store_as_csv():
    print(os.getcwd())
    map = load_game_rules_to_df()
    map.to_csv("data/game_rules.csv", index=False)

    map = load_map_to_df()
    map.to_csv("data/map.csv", index=False)
