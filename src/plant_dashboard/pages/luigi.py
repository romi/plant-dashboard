#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dash import html
from dash import register_page

register_page(__name__, path_template="/luigi")

layout = html.Div([
    html.Iframe(id="external_page_iframe",
                src="http://localhost:8082/static/visualiser/index.html",
                style={"width": "100%", "height": "100vh"}),
])
