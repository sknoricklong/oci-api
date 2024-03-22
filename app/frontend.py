import asyncio
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Request, Depends, FastAPI, HTTPException, status
import httpx
from requests import post
from nicegui import Client, app, ui
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from fastapi_sso.sso.google import GoogleSSO

from .loader import load_cities, load_law_schools, load_law_firms
from .datagrid import DataGrid
from .config import settings
from . import oauth2
from .database import get_db
from .models import User


def init(fastapi_app: FastAPI) -> None:
    unrestricted_page_routes = {'/login'}

    class AuthMiddleware(BaseHTTPMiddleware):
        """This middleware restricts access to all NiceGUI pages.

        It redirects the user to the login page if they are not authenticated.
        """

        async def dispatch(self, request: Request, call_next):
            if not app.storage.user.get('authenticated', True):
                if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                    app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                    return RedirectResponse('/login')
            return await call_next(request)

    app.add_middleware(AuthMiddleware)

    @ui.page('/')
    def root() -> Optional[RedirectResponse]:
        if app.storage.user.get('authenticated', True):
            return RedirectResponse('/login')  # Redirect to /me if user is authenticated
        else:
            return RedirectResponse('/me')  # Redirect to login if user is not authenticated

    # Assuming your OAuth initialization is done here or imported
    oauth = OAuth()
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        client_kwargs={
            'scope': 'email openid profile'
        }
    )

    def get_google_sso() -> GoogleSSO:
        return GoogleSSO(settings.google_client_id, settings.google_client_secret, redirect_uri=f"{settings.url}:{settings.port}/auth")

    @app.get('/login/google')
    async def google_login(google_sso: GoogleSSO = Depends(get_google_sso)):
        return await google_sso.get_login_redirect()

    @app.get('/auth')
    async def google_callback(request: Request, google_sso: GoogleSSO = Depends(get_google_sso), db: Session = Depends(get_db)):
        user = await google_sso.verify_and_process(request)
        print(user)

        if user:
            email = user.email
            first_name = user.first_name
            print(first_name)
            user = db.query(User).filter(User.email == email).first()
            if not user:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f'{settings.url}:{settings.port}/users/create',  # Adjust URL to your FastAPI backend
                        json={
                            "email": email,
                            "password": settings.google_password
                        })

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{settings.url}:{settings.port}/login',  # Adjust the URL to your FastAPI backend
                    data={
                        'username': email,
                        'password': settings.google_password
                    }
                )
                if response.status_code == 200:
                    token_data = response.json()
                    app.storage.user.update({
                        'authenticated': True,
                        'token': token_data['access_token']
                    })

                    app.storage.user['email'] = email
                    app.storage.user['first_name'] = first_name

                    law_schools_df = load_law_schools()
                    email_domain = email.split('@')[-1]
                    domain_parts = email_domain.split('.')
                    if 'edu' in domain_parts:
                        domain_index = domain_parts.index('edu')
                        matched_domain = '.'.join(domain_parts[domain_index - 1:])
                    else:
                        matched_domain = 'NOT FOUND'

                    # Attempt to match the domain to a school
                    matched_schools = law_schools_df.loc[
                        law_schools_df['Domain'].str.contains(matched_domain, case=False, na=False), 'School'].values
                    print(matched_schools)
                    # Only set 'school' in app.storage.user if a default school is found
                    if len(matched_schools) > 0:
                        default_school = matched_schools[0]  # Only set if there's at least one match
                        app.storage.user['school'] = default_school

                        async with httpx.AsyncClient() as client:
                            await client.put(
                                f'{settings.url}:{settings.port}/profiles/me',  # Adjust URL to your FastAPI backend
                                json={'school': default_school},
                                headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
                            )

        return RedirectResponse('me')


    @ui.page('/login')
    async def login() -> Optional[RedirectResponse]:  # type: ignore
        def try_google_login():
            ui.open('/login/google')

        with ui.card().classes('absolute-center w-96'):

            ui.add_head_html('''
                        <style>
                            /* Apply a warm background color to the entire page */
                            body {
                                background-color:#add8e6; /*
                            }
                            .centered-container {
                                display: flex;
                                justify-content: space-around; /* Adjust spacing */
                                align-items: center;
                                flex-direction: column;
                                height: 100%; /* Ensure it takes full available height */
                            }
                            .full-width {
                                width: 100%;
                                text-align: center; /* Center text for markdown and buttons */
                            }
                            .light-blue-text {
                                color: #e7f3f8; /* Light blue color */
                            }
                            /* Enhanced card styling */
                            .card {
                                background-color: #FFFFFF; /* Light background for the card */
                                padding: 20px; /* Add some padding */
                                border-radius: 8px; /* Rounded corners */
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Subtle shadow */
                            }
                            /* Adjustments for specific elements if needed */
                            .oci-tracker, .join-students, .login-button {
                                flex: 1; /* Allow each item to take equal space */
                                display: flex;
                                justify-content: center;
                                align-items: center;
                            }
                            /* You might need to adjust selectors based on actual rendered HTML */
                        </style>
                    ''')

            async with httpx.AsyncClient() as client:
                response = await client.get(f'{settings.url}:{settings.port}/applications/total')
                if response.status_code == 200:
                    data = response.json()
                    app.storage.user['total_applications'] = data['total_applications']
                    app.storage.user['total_users'] = data['total_users']
                else:
                    return "Error fetching applications"

            ui.markdown("###OCI Tracker###").classes('full-width')
            # Use the 'light-blue-text' class for numbers
            ui.markdown(
                f"""Join {app.storage.user.get('total_users')} students who've submitted {app.storage.user.get('total_applications')} applications.""").classes(
                'full-width')
            ui.button('Enter with School Email', icon='email', on_click=try_google_login).classes('full-width')

    async def create_new_application(client):
        application_data = {}
        response = await client.post(
            f'{settings.url}:{settings.port}/applications/',
            json=application_data,
            headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
        )
        return response.json()


    @ui.page('/me')
    async def show():

        with ui.header().classes('items-center justify-between'):
            # OCI Tracker label with specified classes for styling
            ui.button(f"{app.storage.user.get('first_name', '').upper()}'S OCI TRACKER", on_click='/me', icon='home').props('flat color=white').classes('text-base font-medium')

            # Logout button with matching styling
            ui.button("Logout", icon='logout',
                      on_click=lambda: (app.storage.user.clear(), ui.open('/login'))).props(
                'flat color=white').classes('text-base font-medium')



        law_schools = load_law_schools()
        law_schools = law_schools['School'].tolist()

        # Fetch default profile data
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{settings.url}:{settings.port}/profiles/me',  # Adjust URL to your FastAPI backend
                headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
            )
            profile_data = response.json()

            app.storage.user['school'] = profile_data.get('school', '')
            app.storage.user['rank'] = profile_data.get('rank', 50)
            app.storage.user['circumstances'] = profile_data.get('circumstances', None)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{settings.url}:{settings.port}/applications/me',
                headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
            )
            if response.status_code == 404 and response.json().get('detail') == 'No applications found':
                applications = await create_new_application(client)
                applications = [applications]
            else:
                applications = [application for application in response.json()]

        async def update_profile(event, field_name):
            new_value = event.value
            async with httpx.AsyncClient() as client:
                await client.put(
                    f'{settings.url}:{settings.port}/profiles/me',  # Adjust URL to your FastAPI backend
                    json={field_name: new_value},
                    headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
                )

        circumstances_options = [
            "Disabled",
            "First Generation",
            "International",
            "Parent",
            "Under-Represented Minority",
            "Veteran"
        ]

        with ui.row():
            ui.markdown()
            ui.markdown("**About You**").classes('full-width')
            school_input = ui.select(label='School', options=law_schools, with_input=True,
                                     on_change=lambda e: update_profile(e, 'school'))
            school_input.value = app.storage.user['school']
            rank_input = ui.number(label='Class Rank', value=app.storage.user['rank'], min=0, max=100, step=5,
                                   on_change=lambda e: update_profile(e, 'rank')).style('min-width: 100px;')
            rank_input.value = app.storage.user['rank']

            circumstances_input = ui.select(label='Unique Circumstances', options=circumstances_options, multiple=True,
                                            on_change=lambda selected_circumstances: update_profile(
                                                selected_circumstances, 'circumstances')).style('min-width: 200px;')
            circumstances_input.value = app.storage.user.get('circumstances', [])

        main_container = ui.column()

        async def add_application(application=None):
            if not application:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f'{settings.url}:{settings.port}/applications/',
                        json={},
                        headers={'Authorization': f'Bearer {app.storage.user.get("token")}'}
                    )

                    if response.status_code == 201:
                        # Ensure this matches the expected structure in DataGrid
                        application_data = response.json()
                        # If the API doesn't return summary_stats, initialize them here
                        application_with_stats = {
                            'application': application_data,  # Assuming application_data has the application details
                            'summary_stats': {'total_users_for_firm': 0, 'success_rate': 0}  # Example default values
                        }

                        new_datagrid = DataGrid(application_with_stats['application'],
                                                application_with_stats['summary_stats'])
                        new_datagrid.render()

                    ui.button(on_click=lambda e: on_button_click(e.sender), icon='add')
            else:
                # Ensure existing application data is passed correctly
                new_datagrid = DataGrid(application.get('application', application), application.get('summary_stats', {}))
                new_datagrid.render()

        async def on_button_click(button: ui.button):
            button.delete()
            await add_application()
            ui.markdown()

        with main_container:
            ui.markdown()

            for application in applications:
                await add_application(application)

            ui.button(on_click=lambda e: on_button_click(e.sender), icon='add')
            ui.markdown()
            ui.markdown()



    ui.run_with(
        fastapi_app,
        storage_secret='pick your private secret here',  # NOTE setting a secret is optional but allows for persistent storage per user
    )

