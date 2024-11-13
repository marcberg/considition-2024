import pandas as pd
import os

def load_data() -> dict:
    folder_path = 'data'

    datasets = {}
    if os.path.exists(folder_path):
        csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        
        for file in csv_files:
            file_name = os.path.splitext(file)[0] 
            file_path = os.path.join(folder_path, file)
            datasets[file_name] = pd.read_csv(file_path)

        print(f'Loaded DataFrames: {", ".join(datasets.keys())}')
    else:
        print(f'The folder {folder_path} does not exist.')

    return datasets

    


