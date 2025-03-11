#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plant Dashboard Web Interface

A modular web application that provides an intuitive interface for interacting with PlantDB, enabling users to browse,
visualize, and reconstruct 3D plant datasets through a REST API-powered system.

Key Features
------------
    - Multi-page dashboard interface with Bootstrap styling
    - Batch analysis and reconstruction capabilities
    - Real-time job queue monitoring
    - PlantDB API integration
    - Background task processing with Celery
    - Interactive navigation with configurable endpoints
    - Environment-aware configuration for API connections

Usage Examples
--------------
To run the dashboard application:
$ python app.py
"""

import os

import dash
import dash_bootstrap_components as dbc
from dash import CeleryManager
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html
from plant3dvision.webui.celery_app import celery_app
from plantdb.rest_api_client import REST_API_PORT
from plantdb.rest_api_client import REST_API_URL
from romitask.utils import get_version

from plant_dashboard.nav import navbar

# Configure application name and title settings
APP_NAME = "Plant_Dashboard"
APP_TITLE = "Plant Dashboard"

# Initialize Celery for handling background tasks
background_callback_manager = CeleryManager(celery_app)

# Create Dash application instance with Bootstrap theming
app = dash.Dash(APP_NAME, title=APP_TITLE,
                use_pages=True,
                background_callback_manager=background_callback_manager,
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

# Define main application layout with data stores and UI components
app.layout = html.Div([
    # Session storage for API configuration
    dcc.Store(id='rest-api-host', data=os.environ.get('REST_API_URL', REST_API_URL), storage_type='session'),
    dcc.Store(id='rest-api-port', data=os.environ.get('REST_API_PORT', REST_API_PORT), storage_type='session'),
    # Memory storage for runtime data
    dcc.Store(id='dataset-id', data=None, storage_type='memory'),
    dcc.Store(id='libraries-version', data={}, storage_type='memory'),
    dcc.Store(id='batch-dataset-ids', data=[], storage_type='memory'),
    # Main UI container with navigation and content area
    html.Div(children=[navbar]),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content',
             children=[dash.page_container],
             style={"margin": 20},
             ),
])


@callback(
    Output('libraries-version', 'data'),
    Input('url', 'pathname'),
)
def get_libraries_version(pathname):
    return get_version()


if __name__ == "__main__":
    app.run(debug=True, port=8000)
