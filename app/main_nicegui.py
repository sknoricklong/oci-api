from nicegui import ui, events
import pandas as pd
from datagrid import DataGrid

from .loader import load_cities, load_law_schools
ui.markdown("###OCI Tracker###")

# Load cities
cities = load_cities()

# Load law schools
law_schools = load_law_schools()

def on_email_change(event):
    global user_email
    user_email = event.value

with ui.row():
    # Email input field
    ui.input(label='Email', placeholder='Enter your email', on_change=on_email_change).classes('w-40')
    ui.select(label='School', options=law_schools, with_input=True, on_change=lambda e: ui.notify(e.value)).classes('w-40')
    ui.number(label='Rank', value=50, min=0, max=100, step=5)

firms_df = pd.read_csv('../src/firms.csv')
firms_df['firm'] = firms_df['firm'].str.replace('(verein)', '').str.strip()
firms = sorted(firms_df['firm'].tolist())

# Define network options
network_options = ["Junior", "Senior", "Reception"]

n_firms = 1

main_container = ui.column()

# Function to add a new DataGrid inside the main container
def add_data_grid():
    new_df = DataGrid(n_firms, firms, cities, network_options)
    new_df.render()  # This will add the new DataGrid to the main container

# Add the initial DataGrid to the main container
df = DataGrid(n_firms, firms, cities, network_options)
df.render()  # This adds the DataGrid to the main container

# Add the "Add" button to the main container
with main_container:
    ui.button('Add Firm', on_click=lambda e: add_data_grid())

ui.run(port=8181)