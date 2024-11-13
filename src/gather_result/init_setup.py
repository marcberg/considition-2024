import pandas as pd 
import numpy as np 
import http.client

from src.data.load_data import load_data
from src.api.send_result import get_result

def collect_grid(rates, months, local=True, key = "name", change_award = True):

    # API details
    api_key = "bb244a0b-6c37-48fa-88f7-0644064e5065"
    game_url = "api.considition.com"
    hostname = "localhost"
    port = 8080

    # Make the API call as usual
    conn = http.client.HTTPConnection(hostname, port) if local else http.client.HTTPSConnection(game_url)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    df = load_data()

    game_rules = df.get('game_rules')
    map = df.get('map')

    first_customers_per_personality = map.sort_values("loan_amount", ascending=False).reset_index().drop_duplicates(subset=key, keep="first") 

    mapName = game_rules['name'].iloc[0]
    budget = float(game_rules['budget'].iloc[0])
    gameLengthInMonths = int(game_rules['gameLengthInMonths'].iloc[0])

    rates.insert(0, 99999999999999999)
    df_interest = pd.DataFrame()
    #print(first_customers_per_personality[key])

    for _, customer in first_customers_per_personality.iterrows(): 
    #for _, customer in map.iterrows():
        print(f"\n\nCustomer: {customer[key]}\t\t\t")
        have_accept_first_rate = False
        name = customer['name']
        df_cust = pd.DataFrame({
            'name' : [name],
            'personality': customer["personality"],
            'environmentalImpact': customer["environmentalImpact"],
            'loan_amount': customer["loan_amount"],
            'capital': customer["capital"],
            'income': customer["income"],
            'monthlyExpenses': customer["monthlyExpenses"],
            'numberOfKids': customer["numberOfKids"],
            'homeMortgage': customer["homeMortgage"],
            'hasStudentLoan': customer["hasStudentLoan"],
            'monthly_surplus': customer["income"] - (customer["monthlyExpenses"] + customer["numberOfKids"]*2000 + ((customer["homeMortgage"]*0.1)/12) + customer["hasStudentLoan"]*1000)
        })

        for index, rate in enumerate(rates):
            print(f"- Current rate: {rate}\t\t")

            for index2, month in enumerate(months):
                print(f"-- Current month: {month}\t\t", end='\r')
                if index2 > 0:
                    prev_score = score
                    prev_score_profit = score_profit
                proposal = [{
                    "CustomerName": name,
                    "YearlyInterestRate": float(rate),
                    "MonthsToPayBackLoan": month,
                }]

                iterations = [{} for _ in range(gameLengthInMonths)]

                award_boolean = True
                for month_iteration in range(gameLengthInMonths):
                    if award_boolean:
                        award_final = "IkeaFoodCoupon"
                        award_boolean = False 
                    else:
                        if change_award:
                            award_final = "IkeaDeliveryCheck"
                        else:
                            award_final = "IkeaFoodCoupon"
                        award_boolean = True 
                    iterations[month_iteration][name] = {"Type": "Award" if (month_iteration+1) % 3 == 0 else "Skip", "Award": award_final if (month_iteration+1) % 3 == 0 else "None"}

                input_data = {
                    "MapName": mapName,
                    "Proposals": proposal,
                    "Iterations": iterations
                }
                df_iter = get_result(input_data=input_data, conn=conn, headers=headers)
                score = df_iter['score_totalScore'].iloc[0]
                score_profit = df_iter['score_totalProfit'].iloc[0]

                df_parameters = pd.DataFrame({
                    'interest': [rate],
                    'months': [month]
                })
                df_cust_iteration = pd.concat([df_cust, df_parameters, df_iter], axis=1)
                df_interest = pd.concat([df_interest, df_cust_iteration], ignore_index=True)
                if index2 > 0: 
                    if (score == prev_score) and (prev_score_profit != 0 | index2 > 60):
                        break

            # Below two if-statements is to save time, we don't need to check higher rates if the previous rate have been declined. 
            # check if they have accepted any rate so far
            if (index > 0) and (not have_accept_first_rate):
                have_accept_first_rate = sum(df_interest['score_totalProfit']) != 0

            # check if they stop accepting the rates given they have accepted any rate. Then stop checking for higher rates. 
            if (index > 0) and have_accept_first_rate:

                filtered_rows1 = df_interest[df_interest['interest'] == rates[index-1]]
                didnt_accept_last_interest = sum(filtered_rows1['score_totalProfit']) == 0

                filtered_rows2 = df_interest[df_interest['interest'] == rates[index]]
                didnt_accept_this_interest = sum(filtered_rows2['score_totalProfit']) == 0

                if didnt_accept_last_interest and didnt_accept_this_interest:
                    break

    df_interest.to_csv('artifacts/df_iterations.csv', index=False)
    df_rate_filtered = df_interest[(df_interest['score_totalProfit'] != 0)] # assuming that 0 will be that they didn't accept since its a low probability it else ends up at 0
    df_min_max_rates = df_rate_filtered.groupby(key)['interest'].agg(acceptedMinInterest=('min'), acceptedMaxInterest=('max')).reset_index()

    person_best_score = df_interest.loc[df_interest.groupby('name')['score_totalScore'].idxmax()]

    df_happy = pd.DataFrame()
    for _, customer in person_best_score.iterrows():
        name = customer["name"]
        df_cust = pd.DataFrame({
            'name' : [name],
            'personality' : customer["personality"]
        })
        
        proposals = []
        iterations = []
        proposals.append({
            "CustomerName": customer['name'],
            "YearlyInterestRate": customer['interest'],
            "MonthsToPayBackLoan": customer['months']
        })
        iter = {customer['name']: {"Type": "Award", "Award": 'IkeaDeliveryCheck'}}
        iterations.append(iter)

        award_boolean = True
        for i in range(1, gameLengthInMonths):
            iterations.append({customer['name']: {"Type": "Award" if (i+1) % 3 == 0 else "Skip", "Award": "IkeaFoodCoupon" if (i+1) % 3 == 0 else "None"}})

            if award_boolean:
                award_final = "IkeaFoodCoupon"
                award_boolean = False 
            else:
                if change_award:
                    award_final = "IkeaDeliveryCheck"
                else:
                    award_final = "IkeaFoodCoupon"
                award_boolean = True 
            iterations[i][name] = {"Type": "Award" if (i+1) % 3 == 0 else "Skip", "Award": award_final if (i+1) % 3 == 0 else "None"}



        input_data = {
            "MapName": mapName,
            "Proposals": proposals,
            "Iterations": iterations
        }

        df_iter = get_result(input_data=input_data, conn=conn, headers=headers)
        df_cust_iteration = pd.concat([df_cust, df_iter], axis=1)
        df_happy = pd.concat([df_happy, df_cust_iteration], ignore_index=True)
        
    conn.close()

    df_happy2 = pd.merge(person_best_score[[key, 'score_happynessScore']], df_happy[[key, 'score_happynessScore']], on=key, how='left')
    df_happy2['happinessdiff'] = df_happy2['score_happynessScore_y'] - df_happy2['score_happynessScore_x']
    df_happy2['happinessEffect'] = df_happy2['score_happynessScore_x'] / df_happy2['score_happynessScore_y']
    estimated_personalities1 = pd.merge(df_min_max_rates, df_happy2[[key, 'happinessEffect']], on=key, how='left')

    df_max_months = df_interest.loc[df_interest['score_totalProfit'] != 0].groupby(key).agg(min_months=('months', 'min'), max_months=('months', 'max')).reset_index()
    estimated_personalities = pd.merge(estimated_personalities1, df_max_months, on=key, how="left")
    estimated_personalities.to_csv('artifacts/df_estimated_personalities.csv', index=False)

    map_estimated_personalities = pd.merge(map, estimated_personalities, on=key, how='left')
    map_estimated_personalities['monthly_surplus'] = map_estimated_personalities["income"] - (map_estimated_personalities["monthlyExpenses"] + map_estimated_personalities["numberOfKids"]*2000 + ((map_estimated_personalities["homeMortgage"]*0.1)/12) + map_estimated_personalities["hasStudentLoan"]*1000)
    map_estimated_personalities.to_csv('artifacts/map_estimated_personalities.csv', index=False)
