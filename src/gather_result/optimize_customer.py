import json
import http.client
import numpy as np
import pandas as pd
import random
import os
from skopt import gp_minimize, gbrt_minimize

from skopt.space import Real, Integer, Categorical
from skopt.utils import use_named_args


# API details
api_key = "bb244a0b-6c37-48fa-88f7-0644064e5065"
game_url = "api.considition.com"
hostname = "localhost"
port = 8080
local = True

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
        
        # Skip early stopping check for random starts
        if self.total_iters <= self.n_random_starts:
            return False

        # After random starts, begin tracking for early stopping
        current_score = res.fun
        if self.best_score is None or current_score < self.best_score - self.min_delta:
            self.best_score = current_score
            self.no_improvement_count = 0
        else:
            self.no_improvement_count += 1

        # Stop if patience is exceeded
        if self.no_improvement_count >= self.patience:
            print(f"Early stopping at iteration {self.total_iters} due to no improvement.")
            return True
        return False
    


num_cores = os.cpu_count()
use_num_cores = (num_cores if num_cores <= 4 
            else num_cores - 1 if num_cores <= 8 
            else num_cores - 2)


def optimize_each_customer(mapName, customer, gameLengthInMonths, min_interest, max_interest, min_loan_duration, max_loan_duration, customer_idx, total_customers, n_random_starts=20, n_calls=500, early_stopping_patience=50, early_stopping_min_delta=100, change_award=True):

    def progress_callback(res, customer_idx=customer_idx, total_customers=total_customers):
        iteration = len(res.x_iters)  # Get the current iteration number
        current_score = round(res.func_vals[-1], 2)  # Get the score for the current iteration
        best_score = round(res.fun, 2)  # Get the best score so far
        print(f"Customer {customer_idx}/{total_customers} - Iteration {iteration}: \tCurrent Score = {current_score}, \tBest Score = {best_score}")


    customer_result = pd.DataFrame()

    param_space = [
        Real(min_interest, max_interest, name="interest_rate"),
        Integer(min_loan_duration, max_loan_duration, name="loan_duration"), 
    ]

    @use_named_args(param_space)
    def objective(interest_rate, loan_duration):
        nonlocal customer_result

        # Convert all parameters to native Python types to avoid serialization issues
        interest_rate = float(interest_rate)
        loan_duration = int(loan_duration)

        # Build list of proposals based on approval status
        proposals = []

        proposals.append({
            "CustomerName": customer,
            "YearlyInterestRate": interest_rate,
            "MonthsToPayBackLoan": loan_duration
        })

        iterations = [
                        {customer: {"Type": "Award" if ((i+1) % 3) == 0 else "Skip", "Award": "IkeaFoodCoupon" if (((i+1) % 3) == 0) and (((i+1) % 2) == 1) 
                                                                                                                else "IkeaDeliveryCheck" if (((i+1) % 3) == 0) and (((i+1) % 2) == 0) and change_award
                                                                                                                    else "IkeaFoodCoupon" if (((i+1) % 3) == 0) and (((i+1) % 2) == 0) 
                                                                                                                        else "None"}} for i in range(gameLengthInMonths)
                    ]

        # Construct the input_data with decline logic integrated
        input_data = {
            "MapName": mapName,
            "Proposals": proposals,
            "Iterations": iterations
        }

        # Make the API call as usual
        conn = http.client.HTTPConnection(hostname, port) if local else http.client.HTTPSConnection(game_url)
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        conn.request("POST", "/game", json.dumps(input_data), headers)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        
        # Try to parse JSON and check response type
        try:
            data = json.loads(body)
            if isinstance(data, dict) and "score" in data:
                score = data["score"].get("totalScore", None)
                totalProfit = data["score"].get("totalProfit", None)
                happynessScore = data["score"].get("happinessScore", None)
                environmentalImpact = data["score"].get("environmentalImpact", None)

                # Add the current iteration's data to the customer_result DataFrame
                iter_data = pd.DataFrame({
                    "mapName": [mapName],
                    "name": [customer],
                    "interest_rate": [interest_rate],
                    "loan_duration": [loan_duration],
                    "totalScore": [score],
                    "totalProfit": [totalProfit],
                    "happynessScore": [happynessScore],
                    "environmentalImpact": [environmentalImpact] 
                })

                customer_result = pd.concat([customer_result, iter_data], ignore_index=True)

                if score is not None:
                    conn.close()
                    return -score  # Return the negative score for minimization
                else:
                    print(f"Error: 'totalScore' not found in score data: {data}")
            else:
                print(f"Error: Unexpected response structure: {data}")
        except json.JSONDecodeError:
            print(f"Error: Response not in JSON format: {body}")
        conn.close()
        return 1e6  # Penalize with a large finite number if the response is invalid or improperly formatted

    #early_stopping_callback = EarlyStopping(patience=early_stopping_patience, min_delta=0.1)
    early_stopping_callback = EarlyStoppingAfterRandomStarts(
        patience=early_stopping_patience, min_delta=early_stopping_min_delta, n_random_starts=n_random_starts
    )
     
    # Run Bayesian Optimization
    #result = gp_minimize(objective, 
    #                     param_space, 
    #                     n_random_starts=n_random_starts, 
    #                     n_calls=n_calls, 
    #                     n_jobs=1, #use_num_cores,
    #                     acq_func="EI", # gp_hedge
    #                     callback=[early_stopping_callback, progress_callback])
    
    # Run Bayesian Optimization
    result = gbrt_minimize(objective, 
                         param_space, 
                         n_random_starts=n_random_starts, 
                         n_calls=n_calls, 
                         n_jobs=use_num_cores,
                         callback=[early_stopping_callback, progress_callback])

    # Print results
    print(f"Finished: {customer}")
    
    return customer_result