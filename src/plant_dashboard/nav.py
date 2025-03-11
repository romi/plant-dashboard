#!/usr/bin/env python
# -*- coding: utf-8 -*-


import dash_bootstrap_components as dbc
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import html

APP_HEADER = "Plant Dashboard"

# Define navigation menu items and their corresponding routes
nav_item = dbc.Nav([
    # Navigation links for different sections of the dashboard
    dbc.NavItem(dbc.NavLink("Batch Analysis", href="/batch_reconstruct")),
    dbc.NavItem(dbc.NavLink("Queue", href="/job_queue")),
    dbc.NavItem(dbc.NavLink("PlantDB", href="/plantdb_api")),
    dbc.NavItem(dbc.NavLink("Luigi", href="/luigi")),
    dbc.NavItem(dbc.NavLink("Tutorial", href="https://docs.romi-project.eu/plant_imager/tutorials/reconstruct_scan/")),
])

# Define navigation bar component using Dash Bootstrap Components
navbar = dbc.Navbar(
    dbc.Container([
        # Logo and brand section with link to external website
        html.A(
            # Create horizontal layout for logo and brand name
            dbc.Row([
                # Logo image column
                dbc.Col(html.Img(src='/assets/favicon_white.png', height="35px")),
                # Brand text column with link to home page
                dbc.Col(dbc.NavbarBrand(APP_HEADER, class_name="ms-1", href="/")),
            ], align="center", class_name="g-0", ),
            href="https://romi-project.eu/", style={"textDecoration": "none"},
        ),
        # Hamburger menu button for mobile view
        dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        # Collapsible navigation menu
        dbc.Collapse(
            # Right-aligned navigation items
            dbc.Nav([nav_item, ], class_name="ms-auto", navbar=True),
            id="navbar-collapse", navbar=True,
        ),
    ]),
    # Set navbar color and bottom margin
    color="#00a960", class_name="mb-2",
)

@callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n_clicks, is_open):
    """Toggle the navbar collapse state.

    This callback function handles the toggling of a collapsible navbar menu,
    it switches the collapse state when the navbar toggler button is clicked.

    Parameters
    ----------
    n_clicks : int or None
        Number of times the navbar toggler has been clicked.
        ``None`` if the button hasn't been clicked yet.
    is_open : bool
        Current state of the navbar collapse component.
        ``True`` if expanded, ``False`` if collapsed.

    Returns
    -------
    bool
        The new state of the 'navbar-collapse' component.
        Returns the opposite of current state if button was clicked,
        otherwise returns the current state unchanged.
    """
    if n_clicks:
        return not is_open
    return is_open
