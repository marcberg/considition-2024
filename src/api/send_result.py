import json
import http.client
import numpy as np
import pandas as pd

def get_result(input_data, conn, headers):

    conn.request("POST", "/game", json.dumps(input_data), headers)
    response = conn.getresponse()
    body = response.read().decode("utf-8")
    
    data = json.loads(body)
    df = pd.DataFrame({
        'score_totalProfit': [data['score'].get('totalProfit')],
        'score_happynessScore': [data['score'].get('happinessScore')],
        'score_environmentalImpact': [data['score'].get('environmentalImpact')],
        'score_totalScore': [data['score'].get('totalScore')],
        'mapName': [data['score'].get('mapName')],
    })

    conn.close()

    return df
