import pandas as pd

def load_cities(file_path='src/us_cities.csv'):
    try:
        cities_df = pd.read_csv(file_path)
        return sorted(cities_df['city'].tolist())
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []

def load_law_schools(file_path='src/law_school_rank.csv'):
    try:
        law_school_df = pd.read_csv(file_path)
        return sorted(law_school_df['School'].tolist())
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []
