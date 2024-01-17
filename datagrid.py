from datetime import datetime
from nicegui import ui, events
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype
from sqlmodel import Field, SQLModel, create_engine, Session
from typing import Dict, Any, AnyStr


class CalendarPicker:
    def __init__(self, range_calculator, update_callback, stage):
        self.range_calculator = range_calculator
        self.update_callback = update_callback  # Callback to update the DataGrid
        self.date_input = None
        self.menu = None
        self.stage = stage

    def create(self, initial_value=''):
        with ui.input('Date', value=initial_value) as self.date_input:
            with self.date_input.add_slot('append'):
                ui.icon('edit_calendar').on('click', self.open_menu).classes('cursor-pointer')
            with ui.menu() as self.menu:
                ui.date().props('range').bind_value(self.date_input, forward=self.on_date_change)

    def open_menu(self):
        if self.menu:
            self.menu.open()

    def on_date_change(self, date_range):
        result = self.range_calculator(date_range, self.stage)
        self.date_input.set_value(result)
        self.update_callback(result)  # Update the DataGrid with the new value

class DataGrid:
    def __init__(self, n_firms, firms, cities, network_options):
        self.df = pd.DataFrame({
            'Firm': ['' for _ in range(n_firms)],  # Set all firms to empty string
            'City': ['' for _ in range(n_firms)],
            'Networked': [[] for _ in range(n_firms)],  # Empty lists for multi-select
            'Applied -> Response': ['' for _ in range(n_firms)],
            'Screener -> Response': ['' for _ in range(n_firms)],
            'Callback -> Response': ['' for _ in range(n_firms)],
            'Outcome': ['' for _ in range(n_firms)]
        })
        self.firms = firms
        self.cities = cities
        self.network_options = network_options

        # Additional structure to store start and end dates
        self.dates_info = {
            'Applied_Start': ['' for _ in range(n_firms)],
            'Applied_End': ['' for _ in range(n_firms)],
            'Screener_Start': ['' for _ in range(n_firms)],
            'Screener_End': ['' for _ in range(n_firms)],
            'Callback_Start': ['' for _ in range(n_firms)],
            'Callback_End': ['' for _ in range(n_firms)],
        }

    def update(self, r: int, c: int, value):
        self.df.iat[r, c] = value

    def update_dates_info(self, stage, r, date_range):
        if isinstance(date_range, str):
            start_date = end_date = date_range
        elif isinstance(date_range, dict):
            start_date = datetime.strptime(date_range['from'], '%Y-%m-%d').date().isoformat()
            end_date = datetime.strptime(date_range['to'], '%Y-%m-%d').date().isoformat()
        else:
            start_date = end_date = ''

    def range_calculator(self, date_range: Dict[str, Any], stage):
        # Check if date_range is a string, return '0 days'
        if isinstance(date_range, str) and ('2023' in date_range or '2024' in date_range):
            date_obj = datetime.strptime(date_range, '%Y-%m-%d').date()
            self.dates_info[f'{stage}_Start'] = date_obj
            self.dates_info[f'{stage}_End'] = date_obj
            return '1 days'
            print(self.dates_info)
        # Check if date_range is not a dictionary
        if not isinstance(date_range, dict):
            return

        # Parse dates and calculate the difference in days
        start = datetime.strptime(date_range['from'], '%Y-%m-%d').date()
        end = datetime.strptime(date_range['to'], '%Y-%m-%d').date()

        self.dates_info[f'{stage}_Start'] = start
        self.dates_info[f'{stage}_End'] = end


        delta = (end - start).days
        return f'{delta + 1} days'

    def add(self):
        # Define the structure of the new row (without the loop)
        new_row = pd.DataFrame({
            'Firm': [''],  # Single empty string for new entry
            'City': [''],
            'Networked': [[]],  # Single empty list for new entry
            'Applied -> Response': [''],
            'Screener -> Response': [''],
            'Callback -> Response': [''],
            'Outcome': ['']
        })

        # Concatenate the new row to the existing DataFrame
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.render_grid()

    def render(self):
        with ui.grid(rows=len(self.df.index) + 1).classes('grid-flow-col'):
            self.render_grid()

    def render_grid(self):
        for c, col in enumerate(self.df.columns):
            ui.label(col).classes('font-bold')
            for r, row in enumerate(self.df.loc[:, col]):
                if col == 'Firm':
                    ui.select(options=self.firms, with_input=True, value=row,
                              on_change=lambda event, r=r, c=c: self.update(r=r, c=c, value=event.value))
                elif col == 'City':
                    ui.select(options=self.cities, with_input=True, value=row,
                              on_change=lambda event, r=r, c=c: self.update(r=r, c=c, value=event.value))
                elif col == "Networked":
                    ui.select(options=self.network_options, multiple=True, value=[]).classes('w-64')
                elif col == "Outcome":
                    ui.select({1: 'Offer', 0: 'Rejection'})
                elif col in ('Applied -> Response', 'Screener -> Response', 'Callback -> Response'):
                    stage = col.split(' -> ')[0]
                    stage = col.split(' -> ')[0]
                    calendar_picker = CalendarPicker(self.range_calculator,
                                                     lambda value, r=r, c=c: self.update(r, c, value), stage=stage)
                    calendar_picker.create(initial_value='Date')

                elif is_bool_dtype(self.df[col].dtype):
                    ui.checkbox(value=row,
                                on_change=lambda event, r=r, c=c: self.update(r=r, c=c, value=event.value))
                elif is_numeric_dtype(self.df[col].dtype):
                    ui.number(value=row,
                              on_change=lambda event, r=r, c=c: self.update(r=r, c=c, value=event.value))
                else:
                    ui.input(value=row,
                             on_change=lambda event, r=r, c=c: self.update(r=r, c=c, value=event.value))

