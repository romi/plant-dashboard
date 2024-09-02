#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A WebUI to browse, visualize and reconstruct dataset from a PlantDB served by a REST API.
"""
import os

import dash
import dash_bootstrap_components as dbc
from dash import CeleryManager
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import dcc
from dash import html

from plant3dvision.webui.celery_app import celery_app
from plantdb.rest_api_client import REST_API_PORT
from plantdb.rest_api_client import REST_API_URL

APP_NAME = "Plant_Dashboard"
APP_TITLE = "Plant Dashboard"
#APP_HEADER = "ROMI Plant Dashboard"
APP_HEADER = "Plant Dashboard"

# Create a CeleryManager to use in Dash APP:
background_callback_manager = CeleryManager(celery_app)
# Instantiate a multipage Dash APP:
app = dash.Dash(APP_NAME, title=APP_TITLE,
                use_pages=True,
                background_callback_manager=background_callback_manager,
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

# -----------------------------------------------------------------------------
# Navigation bar
# -----------------------------------------------------------------------------
# Navigation links
nav_item = dbc.Nav([
    dbc.NavItem(
        dbc.NavLink("Batch Analysis",
                    href="/batch_reconstruct")
    ),
    dbc.NavItem(
        dbc.NavLink("Queue",
                    href="/job_queue")
    ),
    dbc.NavItem(
        dbc.NavLink("PlantDB",
                    href="/plantdb_api")
    ),
    dbc.NavItem(
        dbc.NavLink("Luigi",
                    href="/luigi")
    ),
    dbc.NavItem(
        dbc.NavLink("Tutorial",
                    href="https://docs.romi-project.eu/plant_imager/tutorials/reconstruct_scan/")
    ),
])

navbar = dbc.Navbar(
    dbc.Container([
        html.A(
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row([
                dbc.Col(html.Img(src='/assets/favicon_white.png', height="35px")),
                dbc.Col(dbc.NavbarBrand(APP_HEADER, class_name="ms-1", href="/")),
            ], align="center", class_name="g-0", ),
            href="https://romi-project.eu/", style={"textDecoration": "none"},
        ),
        dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        dbc.Collapse(
            dbc.Nav([nav_item, ], class_name="ms-auto", navbar=True),
            id="navbar-collapse", navbar=True,
        ),
    ]),
    color="#00a960", class_name="mb-2",
)

app.layout = html.Div([
    # - Initialize the shared data ID:
    dcc.Store(id='rest-api-host', data=os.environ.get('REST_API_URL', REST_API_URL), storage_type='session'),
    dcc.Store(id='rest-api-port', data=os.environ.get('REST_API_PORT', REST_API_PORT), storage_type='session'),
    dcc.Store(id='dataset-id', data=None, storage_type='memory'),
    dcc.Store(id='libraries-version', data={}, storage_type='memory'),
    # Create the list to store selected batch dataset:
    dcc.Store(id='batch-dataset-ids', data=[], storage_type='memory'),
    # - Layout
    html.Div(children=[navbar]),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content',
             children=[dash.page_container],
             style={"margin": 20},
             ),
])


@callback(Output('libraries-version', 'data'),
          Input('url', 'pathname'))
def get_libraries_version(pathname):
    from romitask.utils import get_version
    return get_version()


# we use a callback to toggle the collapse on small screens
@callback(Output("navbar-collapse", "is_open"),
          [Input("navbar-toggler", "n_clicks")],
          [State("navbar-collapse", "is_open")])
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run(debug=True, port=8000)
