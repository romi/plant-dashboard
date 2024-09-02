#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import dcc
from dash import html
from dash import register_page

from plant3dvision.visu import plotly_image_carousel
from plant3dvision.webui.utils import FONT_FAMILY
from plant3dvision.webui.utils import IMAGE_TASKS
from plantdb.rest_api_client import get_images_from_task
from plantdb.rest_api_client import get_tasks_fileset_from_api

register_page(__name__, path_template="/carousel/<dataset_id>")


def layout(dataset_id=None, **kwargs):
    """Create the page layout for the carousel page.

    Parameters
    ----------
    dataset_id : str
        The name of the dataset to show in the carousel page.

    Returns
    -------
    html.Div
        The layout for the carousel page.
    """
    return html.Div([
        # Store the dataset id to use in the callback.
        dcc.Store(id='dataset-id', data=dataset_id),
        # Add a dropdown selector for task images to use as images sources:
        html.Div([
            "Select image task:",
            dcc.Dropdown(
                id="select-image-task",
                value='images',
                clearable=False,
                searchable=False,
                multi=False,
            ),
        ], style={"width": "200px"}
        ),
        # Part where the carousel will be displayed:
        dcc.Loading([dcc.Graph(id='carousel', style={'height': '84vh'}, config={'responsive': True})])
        # For explanations on 'config={'responsive': True}', see:
        # https://dash.plotly.com/dash-core-components/graph#graph-resizing-and-responsiveness
    ])


# Callback to initialize the available dropdown option (list of image related tasks):
@callback(
    Output('select-image-task', 'options'),
    Input('dataset-id', 'data'),
    State('rest-api-host', 'data'),
    State('rest-api-port', 'data')
)
def update_image_task_dropdown(dataset_id, host, port):
    tasks_fileset = get_tasks_fileset_from_api(dataset_id, host=host, port=port)
    return [task for task in IMAGE_TASKS if task in tasks_fileset]


@callback(Output('carousel', 'figure'),
          Input('dataset-id', 'data'),
          Input("select-image-task", "value"),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'))
def images_carousel(dataset_id, task, host, port):
    images = get_images_from_task(dataset_id, task_name=task, size='orig', host=host, port=port)
    fig_layout_kwargs = {'font_family': FONT_FAMILY, 'paper_bgcolor': "#F3F3F3",
                         'autosize': True, 'margin': {'t': 25, 'b': 5}, 'width': None, 'height': None}
    fig = plotly_image_carousel(images, title=None, layout_kwargs=fig_layout_kwargs)
    fig.update_layout(uirevision='value')

    # Remove the axis ticks and labels:
    fig.update_layout(xaxis={'visible': False}, yaxis={'visible': False})
    return fig
