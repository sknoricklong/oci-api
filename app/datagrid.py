import asyncio
from datetime import datetime
import httpx
from nicegui import app, ui
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, AnyStr

from .config import settings
from .loader import load_cities, load_law_firms


class CalendarPicker():
    def __init__(self, range_calculator, update_callback, stage, date_input=None):
        self.range_calculator = range_calculator
        self.update_callback = update_callback
        self.date_input = date_input
        self.menu = None
        self.stage = stage

    def create(self, initial_value=''):
        with ui.input('Date', value=initial_value) as self.date_input:
            with self.date_input.add_slot('append'):
                ui.icon('edit_calendar').on('click', self.open_menu).classes('cursor-pointer')
            with ui.menu() as self.menu:
                calendar = ui.date(on_change=lambda: self.on_date_change(calendar.value)).props('range')
                calendar.value = initial_value

    def open_menu(self):
        if self.menu:
            self.menu.open()

    def on_date_change(self, date_range):
        result = self.range_calculator(date_range, self.stage)
        if result:
            self.date_input.set_value(result)
            self.update_callback(self.stage, result)

class DataGrid:
    def __init__(self, existing_application=None, summary_stats=None):
        self.network_options = ["Junior", "Senior", "Reception"]
        self.firms = load_law_firms()
        self.cities = load_cities()
        self.summary_stats = summary_stats or {}
        self.application_id = existing_application.get('application_id') if existing_application else None
        self.df = pd.DataFrame([{
            key: existing_application.get(key, None) for key in ['firm', 'city', 'networked', 'applied_to_response', 'screener_to_response', 'callback_to_response', 'stage']
        }])

        self.applied_to_response = existing_application.get('applied_to_response',
                                                            None) if existing_application else None
        self.screener_to_response = existing_application.get('screener_to_response',
                                                             None) if existing_application else None
        self.callback_to_response = existing_application.get('callback_to_response',
                                                             None) if existing_application else None

        self.df = pd.DataFrame([{
            'Firm': existing_application.get('firm', None) if existing_application else None,
            'City': existing_application.get('city', None) if existing_application else None,
            'Networked': existing_application.get('networked', None) if existing_application else None,
            'Applied -> Response': existing_application.get('applied_to_response',
                                                            None) if existing_application else None,
            'Screener -> Response': existing_application.get('screener_to_response',
                                                             None) if existing_application else None,
            'Callback -> Response': existing_application.get('callback_to_response',
                                                             None) if existing_application else None,
            'Stage': existing_application.get('stage', None) if existing_application else None
        }])

        self.dates_info = {
            'Applied_Start': datetime.strptime(existing_application.get('applied_date', ''),
                                               '%Y-%m-%d').date() if existing_application and existing_application.get(
                'applied_date') else None,
            'Applied_End': datetime.strptime(existing_application.get('applied_response_date', ''),
                                             '%Y-%m-%d').date() if existing_application and existing_application.get(
                'applied_response_date') else None,
            'Screener_Start': datetime.strptime(existing_application.get('screener_date', ''),
                                                '%Y-%m-%d').date() if existing_application and existing_application.get(
                'screener_date') else None,
            'Screener_End': datetime.strptime(existing_application.get('screener_response_date', ''),
                                              '%Y-%m-%d').date() if existing_application and existing_application.get(
                'screener_response_date') else None,
            'Callback_Start': datetime.strptime(existing_application.get('callback_date', ''),
                                                '%Y-%m-%d').date() if existing_application and existing_application.get(
                'callback_date') else None,
            'Callback_End': datetime.strptime(existing_application.get('callback_response_date', ''),
                                              '%Y-%m-%d').date() if existing_application and existing_application.get(
                'callback_response_date') else None,
        }

        self.api_mapping = {
            'Firm': 'firm',
            'City': 'city',
            'Networked': 'networked',
            'Applied -> Response': 'applied_to_response',
            'Screener -> Response': 'screener_to_response',
            'Callback -> Response': 'callback_to_response',
            'Stage': 'stage',
            'Applied_Start': 'applied_date',
            'Applied_End': 'applied_response_date',
            'Screener_Start': 'screener_date',
            'Screener_End': 'screener_response_date',
            'Callback_Start': 'callback_date',
            'Callback_End': 'callback_response_date'
        }

        self.stage_to_field_mapping = {
            'Screener': 'screener_to_response',
            'Callback': 'callback_to_response',
            'Applied': 'applied_to_response'
        }

    async def make_api_call(self, url, method="post", data=None):
        headers = {'Authorization': f'Bearer {app.storage.user.get("token")}'}
        async with httpx.AsyncClient() as client:
            if method == "post":
                response = await client.post(url, json=data, headers=headers)
            elif method == "put":
                response = await client.put(url, json=data, headers=headers)
            return response

    async def create_application(self):
        application_data = {
        }

        response = await self.make_api_call(f'http://127.0.0.1:{settings.port}/applications/', "post", application_data)

        if response.status_code == httpx.codes.CREATED:
            new_application = response.json()
            self.application_id = new_application['application_id']
            # Optionally update other properties based on the response
            self.update_app_storage_with_prefix(new_application)
        else:
            # Handle the error appropriately
            print(f"Failed to create application: {response.text}")

    async def update_date_application(self, stage, date_range):
        """Handle the updating of date fields."""
        if isinstance(date_range, str):
            start_date = end_date = date_range
        elif isinstance(date_range, dict):
            start_date = datetime.strptime(date_range['from'], '%Y-%m-%d').date().isoformat()
            end_date = datetime.strptime(date_range['to'], '%Y-%m-%d').date().isoformat()
        else:
            start_date = end_date = None

    def range_calculator(self, date_range: Dict[str, Any], stage):
        # Check if date_range is a string, return '0 days'
        if isinstance(date_range, str) and ('2023' in date_range or '2024' in date_range):
            date_obj = datetime.strptime(date_range, '%Y-%m-%d').date()
            self.dates_info.update({f'{stage}_Start': date_obj, f'{stage}_End': date_obj})
            start = end = date_obj
            # Update the date in the application here
            asyncio.create_task(self.update_date_ranges_api(stage, start, end, 1))
            return '1 day'

        # Check if date_range is not a dictionary
        if not isinstance(date_range, dict):
            return

        # Parse dates and calculate the difference in days
        start = datetime.strptime(date_range['from'], '%Y-%m-%d').date()
        end = datetime.strptime(date_range['to'], '%Y-%m-%d').date()

        self.dates_info.update({f'{stage}_Start': start, f'{stage}_End': end})

        delta = (end - start).days
        delta += 1
        asyncio.create_task(self.update_date_ranges_api(stage, start, end, delta))


        return f'{delta} days'

    async def update_date_ranges_api(self, stage, start, end, delta):
        """Asynchronously update the date ranges in the API."""

        field = self.stage_to_field_mapping.get(stage, None)

        # Prepare the data for the API
        update_data = {
            "application_id": self.application_id,
            self.api_mapping[f'{stage}_Start']: start.isoformat(),
            self.api_mapping[f'{stage}_End']: end.isoformat(),
            field: delta
        }
        await self.make_api_call(f'http://127.0.0.1:{settings.port}/applications/{self.application_id}', "put", update_data)

    def add(self):
        # Define the structure of the new row (without the loop)
        new_row = pd.DataFrame({
            'Firm': [''],  # Single empty string for new entry
            'City': [''],
            'Networked': [[]],  # Single empty list for new entry
            'Applied -> Response': [''],
            'Screener -> Response': [''],
            'Callback -> Response': [''],
            'Stage': ['']
        })

        # Concatenate the new row to the existing DataFrame
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.render_grid()

    def render(self):
        with ui.grid(rows=len(self.df.index) + 1).classes('grid-flow-col'):
            self.render_grid()

        with ui.row():
            with ui.column():
                self.render_first_movement_table()
                ui.markdown()

            with ui.column():
                self.render_summary_stats_table()
                ui.markdown()
                ui.markdown()

            with ui.column():
                self.render_median_response_chart()
                ui.markdown()
                ui.markdown()


    async def update_application(self, r, c, value, key):
        """Update DataFrame and store the value in app.storage.user, then send update to API."""
        self.df.iat[r, c] = value
        # app.storage.user[key] = value

        # Extract application_id and field name from key
        application_id, field_name = key.split('-', 1)

        # Convert UI field name to API field name
        api_field_name = self.api_mapping[field_name]

        # Prepare the data for the API
        update_data = {api_field_name: value}

        # Send update request to the API
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f'http://127.0.0.1:{settings.port}/applications/{application_id}',  # Adjust URL as needed
                json=update_data,
                headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
            )

            if response.status_code == httpx.codes.OK:
                updated_application = response.json()
                self.update_app_storage_with_prefix(updated_application)
                self.summary_stats = updated_application['summary_stats']

                self.update_ui_summary_stats()

    def update_ui_summary_stats(self):
        # Assume self.summary_stats is already updated with the latest data.

        # Update the Summary Stats Table
        granular_success_rates = self.summary_stats.get('success_rate_granular', {})
        summary_stats_data = []

        for key, value in granular_success_rates.items():
            metric_name = ' '.join(key.replace('_rate', '').split('_')).title()
            rate = f"{value['rate']:.0f}% ({value['numerator']} of {value['denominator']})"
            summary_stats_data.append({'Stage': metric_name, 'Rate': rate})

        # Here, instead of adding rows to an existing table, we create a new table instance with updated data.
        # This assumes that self.table refers to a UI component that can be replaced or updated.
        self.table.rows = summary_stats_data
        self.table.update()

        # Update the Chart with new data
        median_responses = self.summary_stats.get('median_responses', {})
        stages = ['Applied', 'Screener', 'Callback']
        success_days = []
        overlay_not_success_days = []

        for stage_key in ['median_applied_to_response', 'median_screener_to_response', 'median_callback_to_response']:
            success = median_responses.get(stage_key, {}).get('success', 0)
            not_success = median_responses.get(stage_key, {}).get('not_success', 0)
            success_days.append(success)
            overlay = not_success - success if not_success > success else 0
            overlay_not_success_days.append(overlay)

        # Assuming self.chart is a Highcharts object or similar, that can dynamically update its data.
        self.chart.options['series'] = [{
            'name': 'Advanced to Next Stage',
            'data': success_days,
            'color': '#6ed458'
        }]
        self.chart.update()

    def render_grid(self):
        for c, col in enumerate(self.df.columns):
            ui.label(col).classes('font-bold')

            for r, row in enumerate(self.df.loc[:, col]):

                key = f'{self.application_id}-{col}'
                current_value = app.storage.user.get(key, row)

                if col == 'Firm':
                    ui.select(label='Firm', options=self.firms, with_input=True, value=current_value,
                              on_change=lambda event, r=r, c=c, key=key: self.update_application(r, c, event.value, key))
                elif col == 'City':
                    ui.select(label='City', options=self.cities, with_input=True, value=current_value,
                              on_change=lambda event, r=r, c=c, key=key: self.update_application(r, c, event.value, key))

                elif col == "Networked":
                    ui.select(label='', options=self.network_options, multiple=True, value=current_value,
                              on_change=lambda event, r=r, c=c, key=key: self.update_application(r, c, event.value, key)).style('width: 195px;')

                elif col == "Stage":

                    ui.select(
                        label='',
                        options={
                            'Not Submitted': 'Not Submitted',
                            'Submitted Application': 'Submitted Application',
                            'Screener Invite': 'Screener Invite',
                            'Callback Invite': 'Callback Invite',
                            'Offer': 'Offer',
                            'Rejection': 'Rejection'
                        },
                        value=current_value,
                        on_change=lambda event, r=r, c=c, key=key: self.update_application(r, c, event.value, key)
                    ).style('width: 200px;')

                if col in ('Applied -> Response', 'Screener -> Response', 'Callback -> Response'):
                    stage = col.split(' -> ')[0]
                    initial_date_range = self.get_initial_date_range_for_stage(stage)
                    calendar_picker = CalendarPicker(self.range_calculator,
                                                     self.update_date_application,
                                                     stage)
                    calendar_picker.create(initial_value=initial_date_range)


    def get_initial_date_range_for_stage(self, stage):
        start_key = f'{stage}_Start'
        end_key = f'{stage}_End'
        if self.dates_info[start_key] and self.dates_info[end_key]:
            return {'from': self.dates_info[start_key].isoformat(), 'to': self.dates_info[end_key].isoformat()}
        return None


    def update_app_storage_with_prefix(self, application_data):
        prefix = f'{self.application_id}_'
        for key, value in application_data.items():
            app.storage.user[prefix + key] = value

    def render_summary_stats_table(self):
        granular_success_rates = self.summary_stats.get('success_rate_granular', {})
        summary_stats_data = []

        # Dynamically create rows for each granular success rate, removing "Rate" from the titles and adjusting the percentage format
        for key, value in granular_success_rates.items():
            # Convert snake_case to Title Case and remove "Rate"
            metric_name = ' '.join(key.replace('_rate', '').split('_')).title()
            # Format the rate to two decimal places
            rate = f"{value['rate']:.0f}% ({value['numerator']} of {value['denominator']})"
            summary_stats_data.append({'Stage': metric_name, 'Rate': rate})

        columns = [
            {'name': 'Stage', 'label': 'Stage', 'field': 'Stage', 'align': 'left'},
            {'name': 'Rate', 'label': 'Rate', 'field': 'Rate', 'align': 'left'}
        ]

        # Use ui.table to render summary_stats_data
        self.table = ui.table(columns=columns, rows=summary_stats_data, row_key='Stage').style('width: 100%')

    def format_date(self, date_str):
        if date_str and date_str != 'N/A':
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d')
        return date_str

    def render_first_movement_table(self):
        start_dates = self.summary_stats.get('start_dates', {})
        first_movement_data = [
            {'First Movement': 'Screeners', 'Date': self.format_date(start_dates.get('screener_start', 'N/A'))},
            {'First Movement': 'Callbacks', 'Date': self.format_date(start_dates.get('callback_start', 'N/A'))},
            {'First Movement': 'Offers', 'Date': self.format_date(start_dates.get('offer_start', 'N/A'))}
        ]

        columns = [
            {'name': 'First Movement', 'label': 'First Movement', 'field': 'First Movement', 'align': 'left'},
            {'name': 'Date', 'label': 'Date', 'field': 'Date', 'align': 'left'}
        ]

        # Use ui.table to render first_movement_data
        self.first_movement_table = ui.table(columns=columns, rows=first_movement_data, row_key='First Movement').style(
            'width: 100%')

    def render_median_response_chart(self):
        median_responses = self.summary_stats.get('median_responses', {})
        stages = ['Applied', 'Screener', 'Callback']
        success_days = []
        applied_to_response = self.applied_to_response

        # Extract success days for each stage
        for stage_key in ['median_applied_to_response', 'median_screener_to_response', 'median_callback_to_response']:
            success = median_responses.get(stage_key, {}).get('success', 0)
            success_days.append(success)

        # Prepare the scatter data for applied_to_response
        scatter_data = [None, None, None]  # Assuming the applied_to_response should be placed in the 'Applied' category
        scatter_data[0] = applied_to_response  # Update this index based on where 'Applied' falls in the `stages` list

        # Configure the chart to display success data and a scatter point for applied_to_response
        self.chart = ui.highchart({
            'chart': {'type': 'bar'},
            'title': {'text': 'Median Days to Response', 'style': {'fontSize': '12px', 'color': 'black'}},
            'xAxis': {'categories': stages},
            'yAxis': {'min': 0, 'title': {'text': 'Days'}},
            'legend': {'reversed': True},
            'plotOptions': {
                'series': {'stacking': 'normal'},
                'scatter': {
                    'marker': {
                        'symbol': 'circle',
                        'radius': 4
                    }
                }
            },
            'series': [
                {
                    'name': 'Advanced to Next Stage',
                    'data': success_days,
                    'color': '#6ed458'
                },
                # {
                #     'type': 'scatter',
                #     'name': 'You',
                #     'data': scatter_data,
                #     'color': '#d458c0'  # This sets the dot to red; adjust as needed
                # }
            ]
        }).classes('w-full h-64')










