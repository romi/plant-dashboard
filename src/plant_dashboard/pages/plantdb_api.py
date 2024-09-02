#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash
import dash_bootstrap_components as dbc
import requests
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import html

from plant3dvision.webui.utils import base_url
from plantdb.rest_api_client import REST_API_PORT
from plantdb.rest_api_client import REST_API_URL
from plantdb.rest_api_client import test_db_availability

global dataset_dict

dash.register_page(__name__, path="/plantdb_api")

# -----------------------------------------------------------------------------
# Forms and callbacks to connect to the PlantDB REST API.
# -----------------------------------------------------------------------------
rest_api_card = dbc.Card(
    id="rest-api-card",
    children=[
        dbc.CardHeader("PlantDB REST API"),
        dbc.CardBody([
            dbc.Row([
                # - Input form to specify REST API URL:
                dbc.Col([
                    dbc.Label("REST API URL:"),
                    dbc.Input(id="ip-address", type="url", value=REST_API_URL),
                    dbc.FormText(f"Use '{REST_API_URL}' for a local database.", color="secondary"),
                ], width=8, ),
                # - Input form to specify REST API port:
                dbc.Col([
                    dbc.Label("REST API port:"),
                    dbc.Input(id="ip-port", type="text", value=REST_API_PORT),
                    dbc.FormText(f"Should be '{REST_API_PORT}' by default.", color="secondary"),
                ], width=4, ),
            ]),
        ]),
        dbc.CardFooter([
            dbc.Row([
                # - Test connexion to REST API button
                dbc.Col([
                    dbc.Button("Test connexion", id="connect-button", color="primary"),
                    dbc.FormText(
                        dbc.Alert([
                            html.I(className="bi bi-info-circle me-2"),
                            "Unknown server availability."
                        ], color="info"),
                        id="connexion-status"),
                ], align="center", ),
                # - Load refresh REST API button
                dbc.Col([
                    dbc.Button("Refresh datasets", id="refresh-button", color="primary", disabled=True),
                    dbc.FormText("", id="refresh-status"),
                ], align="center", ),
            ])
        ], style={"align-content": 'center'})

    ]
)

layout = html.Div([
    # Content of the scan page:
    dbc.Button("< Back", href="/", style={'width': '200px'}),
    html.Br(),
    dbc.Row(
        id="conf-page-content",
        children=[
            dbc.Col(rest_api_card, md=6),
        ]
    )
])


@callback(Output('connexion-status', 'children'),
          Output('refresh-button', 'disabled'),
          Output('rest-api-host', 'data'),
          Output('rest-api-port', 'data'),
          Input('connect-button', 'n_clicks'),
          State('ip-address', 'value'),
          State('ip-port', 'value'))
def test_connect(n_clicks, host, port):
    is_avail = test_db_availability(host, int(port))
    if is_avail:
        res = dbc.Alert([
            html.I(className="bi bi-check-circle-fill me-2"),
            "Server available.",
        ], color="success", )
    else:
        res = dbc.Alert([
            html.I(className="bi bi-x-octagon-fill me-2"),
            f"Server {host}:{port} unavailable!",
        ], color="danger", )
    return res, not is_avail, host, port


@callback(Output('refresh-status', 'children'),
          Input('refresh-button', 'n_clicks'),
          State('ip-address', 'value'),
          State('ip-port', 'value'),
          prevent_initial_call=True)
def refresh_db(n_clicks, host, port):
    if n_clicks > 0:
        req = requests.get(f'{base_url(host, port)}/refresh')
        if req.ok:
            res = dbc.Alert([
                html.I(className="bi bi-check-circle-fill me-2"),
                f"Successfully refreshed database {host}:{port}.",
            ], color="success", )
        else:
            res = dbc.Alert([
                html.I(className="bi bi-x-octagon-fill me-2"),
                f"Could not refresh database {host}:{port}!",
            ], color="danger", )
        return res
    else:
        return ""
