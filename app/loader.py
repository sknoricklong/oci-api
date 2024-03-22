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
        return law_school_df[['School', 'Domain']].sort_values(by='School').reset_index(drop=True)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return pd.DataFrame(columns=['School', 'Domain'])

def load_law_firms(file_path='src/firms.csv'):
    try:
        firms_df = pd.read_csv(file_path)
        return sorted(firms_df['firm'].tolist())
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []