#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import dcc
from dash import html
from dash import register_page

from plant3dvision.webui.utils import _carousel_href
from plant3dvision.webui.utils import _reconstruct_href
from plant3dvision.webui.utils import _viewer_href
from plant3dvision.webui.utils import base_url
from plant3dvision.webui.utils import get_dataset_dict

register_page(__name__, path='/')

# -----------------------------------------------------------------------------
# Table
# -----------------------------------------------------------------------------

TASKS = [
    "Colmap",
    "PointCloud",
    "TriangleMesh",
    "CurveSkeleton",
    "TreeGraph",
    "AnglesAndInternodes",
]

layout = html.Div([
    html.Div([
        dbc.Button([html.I(className="bi bi-arrow-clockwise me-2"), "Refresh"],
                   id='refresh-table-button', color="primary", outline=True, n_clicks=0),
        dbc.Button([html.I(className="bi bi-question-lg")],
                   id='home-table-help', color="secondary", outline=True, n_clicks=0),
        dbc.Popover([
            dbc.PopoverHeader("Help!"),
            dbc.PopoverBody([
                html.P(["You may sort the table by clicking on a column header."]),
                html.P(["Except for the 'Thumbnail' & 'Action' columns,",
                        "you can filter the displayed data by columns using the ",
                        html.I(className="bi bi-list"),
                        " icon that appears on hover and typing a query."]),
                html.P(["Note that the tasks column filters are `Yes` or `No`."]),
                html.P(["You can drag the columns to reorder them."])
            ])
        ], target="home-table-help", trigger='legacy'),
    ],
        style={"width": "100%", 'display': 'flex', 'justify-content': 'flex-end',
               'margin-bottom': '5px', 'gap': '10px'},
    ),
    dcc.Loading([
        dcc.Store(id='dataset-dict', data=None, storage_type='session'),
        html.Div(id="dataset-table", style={"width": "100%", "height": "84vh"})
    ], target_components={"dataset-dict": "data", "dataset-table": "children"}),
])


def _column_defs(col_name):
    """Set the properties of the AG Grid columns."""
    no_filter_cols = ["Thumbnail", "Action"]
    cdef = {"field": col_name, 'filter': True if col_name not in no_filter_cols else False}
    # Enable markdown rendering to include images and icons:
    if col_name in ["Thumbnail"]:
        cdef["cellRenderer"] = "markdown"
        cdef["cellStyle"] = {'textAlign': 'center'}
    if col_name in TASKS:
        cdef["cellRenderer"] = "TaskIcon"  # defined in assets/dashAgGridComponentFunctions.js
        cdef["cellStyle"] = {'textAlign': 'center'}
    if col_name == "Action":
        cdef["cellRenderer"] = "DropdownLinks"  # defined in assets/dashAgGridComponentFunctions.js
        cdef["cellStyle"] = {"overflow": "visible"}

    return cdef


def _action_menu(dataset_id):
    """Create the dropdown menu to display in the AG Grid 'Action' column.

    Parameters
    ----------
    dataset_id : str
        The id of the dataset, used to create the redirection links.

    Returns
    -------
    list
        The list of 3-tuples used by the `DropdownLinks` JS function to populate the "Links" dropdown menu.
    """
    carousel_menu = ('bi bi-images me-2', "Carousel", _carousel_href(dataset_id))
    reconstruct_menu = ('bi bi-cpu me-2', "Reconstruct", _reconstruct_href(dataset_id))
    viewer_menu = ('bi bi-badge-3d me-2', "3D viewer", _viewer_href(dataset_id))
    return [carousel_menu, reconstruct_menu, viewer_menu]


@callback(Output('dataset-dict', 'data'),
          Output('refresh-table-button', 'n_clicks'),
          Input('url', 'pathname'),
          Input('refresh-table-button', 'n_clicks'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          State('dataset-dict', 'data'))
def update_stored_db(url, n_clicks, host, port, dataset_dict):
    """Update the stored dataset dictionary.

    This is done upon landing on the home (/) or batch (/batch_reconstruct) pages or clicking the refresh button.

    Parameters
    ----------
    url : str
       The current page URL.
    n_clicks: int
       The number of clicks made on the refresh button.
    host : str
       The IP address of the PlantDB REST API.
    port : int
        The port of the PlantDB REST API.
    dataset_dict : dict
        The currently stored dataset dictionary.

    Returns
    -------
    dict
        The updated dataset dictionary.
    int
        Always `0` to re-initialize the number of clicks made on the refresh button.
    """
    if n_clicks > 0 or (url in ["/", '/batch_reconstruct'] and dataset_dict is not None):
        dataset_dict = get_dataset_dict(host, port)
    else:
        dataset_dict = None
    return dataset_dict, 0


@callback(Output('dataset-table', 'children'),
          Input('dataset-dict', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'))
def update_table(dataset_dict, url, port):
    """Update the AG Grid table.

    Parameters
    ----------
    dataset_dict : dict
        The currently stored dataset dictionary.
    host : str
       The IP address of the PlantDB REST API.
    port : int
        The port of the PlantDB REST API.

    Returns
    -------
    dash_ag_grid.AgGrid
        The AG Grid to display.
    """
    thumb_size = 150  # max width or height
    n_rows = 10
    if dataset_dict is not None:
        table_dict = {col: [] for col in ["Thumbnail", "Name", "Action", "Date", "Species", "Images"] + TASKS}
        api_url = base_url(url, port)
        for ds_id, md in dataset_dict.items():
            thumbnail_url = md["thumbnailUri"].replace('thumb', f'{thumb_size}')
            # Include the first image thumbnail and a link to the carousel
            table_dict["Thumbnail"].append(
                f"[![thumbnail]({api_url}{thumbnail_url})]({_carousel_href(ds_id)})"
            )
            table_dict["Name"].append(ds_id)
            table_dict["Action"].append(_action_menu(ds_id))
            table_dict["Date"].append(md["metadata"]["date"])
            table_dict["Species"].append(md["metadata"]["species"])
            table_dict["Images"].append(md["metadata"]["nbPhotos"])
            # Use icons to indicate tasks status:
            for task in TASKS:
                table_dict[task].append('check-circle,green' if md[f"has{task}"] else 'x-circle,red')
        df = pd.DataFrame().from_dict(table_dict)
        table = dag.AgGrid(
            id="plantdb-dag",
            rowData=df.to_dict("records"),
            columnDefs=[_column_defs(col) for col in df.columns],
            getRowId="params.data.Name",
            dashGridOptions={
                "rowHeight": 'auto', "animateRows": False,
                "pagination": True, "paginationAutoPageSize": True,
            },
            persistence=True,
            persisted_props=["filterModel"],
            columnSize="autoSize",
            style={"height": 48 + thumb_size * n_rows + 48, "width": "100%"},
        )
    else:
        table = "No dataset loaded yet!"
    return table
