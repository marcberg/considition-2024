import argparse
import os
from datetime import datetime
import pandas as pd
import numpy as np
import json
import http.client

from skopt import gp_minimize, gbrt_minimize
from skopt.space import Real, Integer, Categorical
from skopt.utils import use_named_args
from pulp import LpMaximize, LpProblem, LpVariable, lpSum

from src.data.store_as_csv import store_as_csv
from src.data.load_data import load_data
from src.gather_result.init_setup import collect_grid
from src.gather_result.optimize_customer import optimize_each_customer
from src.gather_result.util import find_month_neighbors, find_neighbors

def main(args):

    if args.part == 'store_csv' or args.part == 'all':

        store_as_csv()

    df = load_data()

    game_rules = df.get('game_rules')
    map = df.get('map')

    mapName = game_rules['name'].iloc[0]
    budget = float(game_rules['budget'].iloc[0])
    gameLengthInMonths = int(game_rules['gameLengthInMonths'].iloc[0])

    rates = [0.001, 0.01, 0.02, 0.03, 0.04, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 5, 10, 100]

    months = range(0, (gameLengthInMonths*10)+1, 12)

    print(f"\nmapName: {mapName}\nbudget: {budget}\ngameLengthInMonths: {gameLengthInMonths}")

    if args.part == 'grid' or args.part == 'all':

        collect_grid(rates=rates, months=months, key="personality", change_award=args.change_award)

    
    if args.part == 'optimize_each_customer' or args.part == 'all':

        print(f"estimate run-time: {round(((1245/25)*map.shape[0]) / 60, 1)/60}")
        map_estimated_personalities = pd.read_csv('artifacts/map_estimated_personalities.csv')

        customer_result = pd.DataFrame()
        for i, customer in map_estimated_personalities.iterrows():

            min_before, max_after = find_neighbors(rates, customer['acceptedMinInterest'], customer['acceptedMaxInterest'])
            min_months_before, max_months_after = find_month_neighbors(months, customer['min_months'], customer['max_months'])

            customer_result_iter = optimize_each_customer(mapName=mapName, 
                                                            customer=customer['name'], 
                                                            gameLengthInMonths = gameLengthInMonths, 
                                                            min_interest=min_before, 
                                                            max_interest=max_after, 
                                                            min_loan_duration=min_months_before, 
                                                            max_loan_duration=max_months_after, 
                                                            customer_idx=i+1, 
                                                            total_customers=map_estimated_personalities.shape[0],
                                                            n_random_starts=100, 
                                                            n_calls=500,
                                                            early_stopping_patience=50, # max 100
                                                            early_stopping_min_delta=1,
                                                            change_award = args.change_award)
            
            customer_result = pd.concat([customer_result, customer_result_iter], ignore_index=True)

        customer_result.to_csv('artifacts/customer_result.csv', index=False)


    if args.part == 'optimize_input' or args.part == 'all':
        customer_result = pd.read_csv('artifacts/customer_result.csv')
        map_estimated_personalities = pd.read_csv('artifacts/map_estimated_personalities.csv')


        class EarlyStoppingAfterRandomStarts:
            def __init__(self, patience, min_delta, n_random_starts):
                self.patience = patience
                self.min_delta = min_delta
                self.n_random_starts = n_random_starts
                self.best_score = None
                self.no_improvement_count = 0
                self.total_iters = 0

            def __call__(self, res):
                self.total_iters += 1
                
                if self.total_iters <= self.n_random_starts:
                    return False

                current_score = res.fun
                if self.best_score is None or current_score < self.best_score - self.min_delta:
                    self.best_score = current_score
                    self.no_improvement_count = 0
                else:
                    self.no_improvement_count += 1

                if self.no_improvement_count >= self.patience:
                    print(f"Early stopping at iteration {self.total_iters} due to no improvement.")
                    return True
                return False
            
        
        api_key = "bb244a0b-6c37-48fa-88f7-0644064e5065"
        game_url = "api.considition.com"
        hostname = "localhost"
        port = 8080
        local = args.optimize_run_local

        df_df = pd.merge(customer_result, map_estimated_personalities[["name", "loan_amount", "happinessEffect"]], on='name', how="left")

        if args.change_award:
            param_space = [
                Real(0, 1000, name="award_cost1"), 
                Real(0, 1000, name="award_cost2"),
            ]
        else:    
            param_space = [
                Real(0, 1000, name="award_cost1"), 
            ]


        def cost_objective(params):
            
            award_cost1 =  params[0]
            if args.change_award:
                award_cost2 =  params[1]

            if args.change_award:
                df_df['totalCost'] = df_df['loan_amount'] + ((award_cost1*int(np.floor(gameLengthInMonths/3)))/2) + ((award_cost2*int(np.floor(gameLengthInMonths/3)))/2) 
            else:
                df_df['totalCost'] = df_df['loan_amount'] + (award_cost1*int(np.floor(gameLengthInMonths/3)))

            df_all = df_df[(df_df['totalScore'] > 0) & (df_df['environmentalImpact'] > 0)][["mapName", "name", "interest_rate", "loan_duration", "totalCost", "totalScore", 'happynessScore']]

            df_all.sort_values(by=["name", "totalCost", "totalScore"], ascending=[True, False, False], inplace=True)

            filtered_rows = []

            for name in df_all['name'].unique():
                name_rows = df_all[df_all['name'] == name]
                
                for i, row in name_rows.iterrows():
                    if not ((name_rows['totalScore'] > row['totalScore']) & (name_rows['totalCost'] < row['totalCost']) & (name_rows['totalCost'] < row['totalCost'])).any():
                        filtered_rows.append(row)

            df_final_filtered = pd.DataFrame(filtered_rows)

            df_grouped = df_final_filtered.groupby('name', group_keys=False).apply(lambda x: x.loc[x['totalScore'].idxmax()])

            df_grouped = pd.concat([df_grouped, pd.DataFrame({
                "mapName": df_grouped['mapName'],
                "name": df_grouped['name'],
                "interest_rate": 0,
                "loan_duration": 0,
                "award_duration": 0,
                "award": "NoSelection",
                "totalCost": 0,
                "totalScore": 0
            })])

            model = LpProblem("Maximize_TotalScore", LpMaximize)

            x = [LpVariable(f"x_{i}", cat="Binary") for i in range(len(df_grouped))]

            model += lpSum([df_grouped['totalScore'].iloc[i] * x[i] for i in range(len(df_grouped))])
            model += lpSum([df_grouped['totalCost'].iloc[i] * x[i] for i in range(len(df_grouped))]) <= budget
            model.solve()

            selected_indices = [i for i in range(len(df_grouped)) if x[i].value() == 1 and df_grouped.iloc[i]["award"] != "NoSelection"]
            optimal_rows = df_grouped.iloc[selected_indices]

            proposals = [
                {
                    "CustomerName": str(customer['name']),
                    "YearlyInterestRate": customer['interest_rate'],
                    "MonthsToPayBackLoan": customer['loan_duration']
                } for _, customer in optimal_rows.iterrows()
            ]

            iterations = [
                {
                    customer['name']: {
                        "Type": "Award" if ((month+1) % 3 == 0) and customer['loan_duration'] <= month else "Skip",
                        "Award": "IkeaFoodCoupon" if (((month+1) % 3 == 0) & ((month+1) % 6 != 0)) and customer['loan_duration'] <= month
                                                    else "IkeaDeliveryCheck" if (((month+1) % 3 == 0) & ((month+1) % 6 == 0)) and args.change_award and customer['loan_duration'] <= month
                                                        else "IkeaFoodCoupon" if (((month+1) % 3 == 0) & ((month+1) % 6 == 0))  and customer['loan_duration'] <= month
                                                            else "None" 
                    }
                    for _, customer in optimal_rows.iterrows()
                }
                for month in range(gameLengthInMonths)
            ]

            input_data = {
                "MapName": mapName,
                "Proposals": proposals,
                "Iterations": iterations
            }

            conn = http.client.HTTPConnection(hostname, port) if local else http.client.HTTPSConnection(game_url)
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
            }

            conn.request("POST", "/game", json.dumps(input_data), headers)
            response = conn.getresponse()
            body = response.read().decode("utf-8")
            
            try:
                data = json.loads(body)
                if isinstance(data, dict) and "score" in data:
                    score = data["score"].get("totalScore", None)

                    if score is not None:
                        conn.close()
                        return -score 
                    else:
                        print(f"Error: 'totalScore' not found in score data: {data}")
                else:
                    print(f"Error: Unexpected response structure: {data}")
            except json.JSONDecodeError:
                print(f"Error: Response not in JSON format: {body}")
            conn.close()
            return 1e6  # Penalize with a large score if the response is invalid or improperly formatted
        
        def progress_callback(res):
            iteration = len(res.x_iters)  
            current_score = round(res.func_vals[-1], 2) 
            best_score = round(res.fun, 2) 
            print(f"Iteration {iteration}: \tCurrent Score = {current_score}, \tBest Score = {best_score}")

        n_random_starts = 10
        n_calls = 500

        early_stopping_callback = EarlyStoppingAfterRandomStarts(
            patience=50, min_delta=1, n_random_starts=n_random_starts
        )
        result = gbrt_minimize(cost_objective, 
                        param_space, 
                        n_random_starts=n_random_starts, 
                        n_calls=n_calls, 
                        n_jobs=1,
                        callback=[early_stopping_callback, progress_callback])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the pipeline or parts of the pipeline.")
    parser.add_argument('--part', type=str, choices=['all', 'store_csv', 'grid', 'optimize_each_customer', 'optimize_input'], default='all')
    parser.add_argument('--change_award', action='store_true')
    parser.add_argument('--optimize_run_local', action='store_false')

    args = parser.parse_args()
    main(args)
