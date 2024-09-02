#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import ClientsideFunction
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import clientside_callback
from dash import ctx
from dash import dcc
from dash import html
from dash import register_page

from plant3dvision.visu import plotly_direction_data
from plant3dvision.visu import plotly_mesh_data
from plant3dvision.visu import plotly_pointcloud_data
from plant3dvision.visu import plotly_treegraph_data
from plant3dvision.visu import plotly_vert_sequences
from plant3dvision.webui.utils import FONT_FAMILY
from plant3dvision.webui.utils import TASK_OBJECTS
from plant3dvision.webui.utils import t_now
from plantdb.rest_api_client import get_scan_data
from plantdb.rest_api_client import get_task_data

register_page(__name__, path_template="/3d_viewer/<dataset_id>")


def get_global_range(pcd, mesh_vertices):
    """Compute the axis range to preserve for 3D viewer using the point cloud and triangular mesh.

    Parameters
    ----------
    pcd : numpy.ndarray
        The loaded point cloud object.
    mesh : numpy.ndarray
        The loaded triangular mesh object.

    Returns
    -------
    list, list
        The minimum & maximum XYZ range.
    """
    # Get the point cloud coordinates and get the mini & maxi for XYZ:
    pcd_arr = np.array(pcd).T
    min_pcd, max_pcd = np.min(pcd_arr, axis=0), np.max(pcd_arr, axis=0)
    # Try to get the triangular mesh mini & maxi for XYZ if defined, else set it to NaN:
    if mesh_vertices is not None:
        # Get triangular mesh vertices coordinates and get the min & max for XYZ:
        mesh_pts = np.array(mesh_vertices).T
        min_mesh, max_mesh = np.min(mesh_pts, axis=0), np.max(mesh_pts, axis=0)
    else:
        min_mesh, max_mesh = np.array([np.nan, np.nan, np.nan]), np.array([np.nan, np.nan, np.nan])
    # Returns the mini & maxi for XYZ
    return list(np.nanmin([min_pcd, min_mesh], axis=0)), list(np.nanmax([max_pcd, max_mesh], axis=0))


def get_axes_ratio(mini, maxi):
    """Compute the XYZ axes ratio for the 3D viewer.

    Parameters
    ----------
    mini : numpy.ndarray
        The minimum XYZ range.
    maxi : numpy.ndarray
        The maximum XYZ range.

    Returns
    -------
    numpy.ndarray
        The XYZ axes ratio.
    """
    axes_range = maxi - mini
    return axes_range / np.max(axes_range)


def get_graph_objects(data):
    """Create `plotly.graph_objects` corresponding to each 3D structures to render.

    Parameters
    ----------
    data : dict
        A dictionary containing the plotly 3D structures to render (`plotly.graph_objects`).

    Returns
    -------
    dict
        The dictionary with `plotly.graph_objects` to render.
    """
    go_data = {obj: None for obj in TASK_OBJECTS}

    if data['PointCloud'] is not None:
        go_data['PointCloud'] = plotly_pointcloud_data(data['PointCloud'], n_pts=9000, showlegend=False)
    if data['TriangleMesh'] is not None:
        go_data['TriangleMesh'] = plotly_mesh_data(data['TriangleMesh'], mesh_kwargs={"opacity": 0.8}, showlegend=False)
    if data['TreeGraph'] is not None:
        go_data['TreeGraph'] = plotly_treegraph_data(data["TreeGraph"],
                                                     legendgroup='tree', legendgrouptitle={'text': 'TreeGraph'})
    if data['FruitDirection'] is not None:
        fruit_dir = data["FruitDirection"]
        go_data['FruitDirection'] = plotly_direction_data(fruit_dir["fruit_dirs"], fruit_dir["bp_coords"], "fruit",
                                                          legendgroup='fruit',
                                                          legendgrouptitle={'text': 'FruitDirection'})
    if data['StemDirection'] is not None:
        stem_dir = data["StemDirection"]
        go_data['StemDirection'] = plotly_direction_data(stem_dir["stem_dirs"], stem_dir["bp_coords"], "stem",
                                                         legendgroup='stem',
                                                         legendgrouptitle={'text': 'StemDirection'})

    return go_data


loading_modal = dbc.Modal([
    dbc.ModalHeader(["Loading data..."]),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([dbc.Spinner(color="primary")], md=2),
            dbc.Col(["Please wait while loading data..."], md=10),
        ])
    ])
], id="loading-modal", is_open=True)

viewer_card = dbc.Card(
    id="viewer-card",
    children=[
        dbc.CardHeader("3D viewer"),
        dbc.CardBody([
            # 3D viewer options:
            html.Div([
                "Structures to display: ",
                dcc.Checklist(id='task-data-checklist', options=TASK_OBJECTS, inline=True,
                              value=["PointCloud"],
                              style={'flex': 1, 'padding': '0px 0px 10px 10px', 'margin': '0px'}),
            ],
                style={'display': 'flex', 'flexDirection': 'row', 'padding': '0px', 'margin': '0px'}),
            # 3D viewer:
            html.Div([
                dcc.Graph(id='3d-viewer-graph', responsive=True),
                html.Div(
                    id='fruit-slider-div',
                    children=[
                        html.Button(html.I(className="bi bi-arrow-up-circle"),
                                    id='fruit-slider-up', n_clicks=0),
                        dcc.RangeSlider(id="fruit-slider", min=-1, max=0, step=1,
                                        vertical=True, verticalHeight=800, allowCross=False, pushable=1, disabled=True),
                        html.Button(html.I(className="bi bi-arrow-down-circle"),
                                    id='fruit-slider-down', n_clicks=0),
                    ]
                ),
            ],
                id='3d-viewer-graph-container',
                style={'width': '100%', 'height': '80vh',
                       'display': 'grid', 'grid-template-columns': '0.95fr 0.05fr',
                       'padding': '0px', 'margin': '0px'},
                **{'data-container-id': '3d-viewer-graph-container'}
            ),
        ])
    ]
)

sequences_card = dbc.Card(
    id="sequences-card",
    children=[
        dbc.CardHeader("Sequences viewer"),
        dbc.CardBody([
            # Sequence graphs options:
            html.Div([
                "Y-axis: ",
                dcc.Dropdown(['index', 'distance'], value='index', id="y-axis-dropdown",
                             clearable=False, multi=False,
                             style={'flex': 1, 'padding': '0px 0px 0px 10px', 'margin': '0px'}),
            ],
                style={'display': 'flex', 'flexDirection': 'row', 'padding': '0px', 'margin': '0px', "width": '15em'}),
            # Sequence graphs:
            html.Div(children=[
                dcc.Graph(id='sequences-graph', responsive=True)
            ],
                id='sequences-graph-container',
                style={'width': '100%', 'height': '80vh', 'padding': '0px', 'margin': '0px'},
                **{'data-container-id': 'sequences-graph-container'}
            ),
        ]),
    ]
)

# Clientside callback to size the 3D viewer graph to fit the `Div` container:
clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='update_graph_dimensions'
    ),
    Output('3d-viewer-graph', 'style'),
    Input('3d-viewer-graph-container', 'style'),
    Input('3d-viewer-graph-container', 'data-container-id')
)

# Clientside callback to size the sequence graph to fit the `Div` container:
clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='update_graph_dimensions'
    ),
    Output('sequences-graph', 'style'),
    Input('sequences-graph-container', 'style'),
    Input('sequences-graph-container', 'data-container-id')
)


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
        dcc.Store(id='dataset-id', data=dataset_id),  # name of the dataset to access in the PlantDB
        dcc.Store(id='dataset-api-info', data={}),  # JSON dictionary from PlantDB REST API for selected `dataset-id`
        dcc.Store(id='data-dict', data={k: None for k in TASK_OBJECTS}),  # dict of 'RAW' data from PlantDB REST API
        dcc.Store(id='data-range', data=None),  # 2-tuple of minimum & maximum range in XYZ
        dcc.Store(id='task-traces', data=[]),  # list data type (pcd, mesh, ...) in the '3d-viewer-graph' figure
        dcc.Store(id='hover-traces', data=None),  # list traces to display on hover or selection of fruits in sequences
        dcc.Store(id='n-fruits', data=0),
        dcc.Store(id='selected-fruits', data=None),
        # dcc.Store(id='loading-state', data="None"),
        # Content of the 3D viewer app:
        dbc.Row(
            id="viewer-app-content",
            children=[
                # dbc.Progress(id='data-loading-progress', value=2, min=0, max=5),
                # dcc.Interval(id="progress-interval", n_intervals=0, interval=500, disabled=True),
                loading_modal,
                dbc.Col(viewer_card, md=7),
                dbc.Col(sequences_card, md=5),
            ],
        ),
    ])


@callback(Output('dataset-api-info', 'data'),
          Input('url', 'pathname'),
          State('dataset-id', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'))
def get_dataset_api_info(pathname, dataset_id, host, port):
    """Get JSON dictionary from PlantDB REST API for corresponding dataset."""
    print(f"[{t_now()}] Callback `get_dataset_api_info`...")
    if pathname.startswith('/3d_viewer'):
        api_kwargs = {"host": host, "port": port}
        api_data = get_scan_data(dataset_id, **api_kwargs)
        print(f"Obtained a JSON dict with {len(api_data)} entries for dataset `{dataset_id}` from '{host}:{port}'!")
        return api_data


@callback(Output('data-dict', 'data'),
          Input('dataset-api-info', 'data'),
          State('dataset-id', 'data'),
          State('data-dict', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          prevent_initial_call=True)
def fetch_data(api_data, dataset_id, data_dict, host, port):
    # TODO : we could use a loading progress bar (using a `dcc.Interval`)...
    print(f"[{t_now()}] Callback `fetch_data`...")
    api_kwargs = {"host": host, "port": port}
    data_dict["PointCloud"] = get_task_data(dataset_id, "PointCloud", api_data=api_data, **api_kwargs)
    print(f"PointCloud loaded: {data_dict['PointCloud'] is not None}")
    data_dict["TriangleMesh"] = get_task_data(dataset_id, "TriangleMesh", api_data=api_data, **api_kwargs)
    print(f"TriangleMesh loaded: {data_dict['TriangleMesh'] is not None}")
    # data_dict["TreeGraph"] = get_task_data(dataset_id, "TreeGraph", api_data=api_data, **api_kwargs)
    data_dict["FruitDirection"] = get_task_data(dataset_id, "AnglesAndInternodes", 'fruit_direction.json',
                                                api_data=api_data, **api_kwargs)
    print(f"FruitDirection loaded: {data_dict['FruitDirection'] is not None}")
    data_dict["StemDirection"] = get_task_data(dataset_id, "AnglesAndInternodes", 'stem_direction.json',
                                               api_data=api_data, **api_kwargs)
    print(f"StemDirection loaded: {data_dict['StemDirection'] is not None}")
    return data_dict


@callback(Output('data-range', 'data'),
          Input("data-dict", 'data'),
          prevent_initial_call=True)
def store_data_range(data_dict):
    """Store the minimum & maximum range in XYZ according to loaded "PointCloud" & "TriangleMesh"."""
    print(f"[{t_now()}] Callback `store_data_range`...")
    pcd = np.array(data_dict["PointCloud"])
    mesh_vertices = np.array(data_dict["TriangleMesh"]["vertices"])
    return get_global_range(pcd, mesh_vertices)


@callback(Output('3d-viewer-graph', 'figure', allow_duplicate=True),
          Output('task-traces', 'data'),
          Output('hover-traces', 'data'),
          Output('loading-modal', 'is_open'),
          Input("data-dict", 'data'),
          State('dataset-api-info', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          prevent_initial_call=True)
def create_3d_graph(data_dict, api_data, host, port):
    """Create `plotly.graph_objects` representations of 'RAW' data from PlantDB REST API."""
    api_kwargs = {"host": host, "port": port}
    print(f"[{t_now()}] Callback `create_graph_objects`...")
    go_data = []
    task_traces = []
    hover_traces = None
    # Create the trace for "PointCloud" data if it exists, else returns an empty figure:
    if api_data['hasPointCloud']:
        print("Creating Plotly representation of 'PointCloud'...")
        go_data.append(plotly_pointcloud_data(data_dict["PointCloud"], n_pts=9000,
                                              name="PointCloud", showlegend=False))
        task_traces.append("PointCloud")
    else:
        return go.Figure()
    # Create the trace for "TriangleMesh" data if it exists:
    if api_data['hasTriangleMesh']:
        print("Creating Plotly representation of 'TriangleMesh'...")
        go_data.append(plotly_mesh_data(data_dict["TriangleMesh"], mesh_kwargs={"opacity": 0.8},
                                        name="TriangleMesh", showlegend=False))
        task_traces.append("TriangleMesh")
    # Create the traces for "TreeGraph" data if it exists:
    if api_data['hasTreeGraph']:
        print("Creating Plotly representation of 'TreeGraph'...")
        dataset_id = api_data["id"]
        tree = get_task_data(dataset_id, "TreeGraph", api_data=api_data, **api_kwargs)
        # Create the list of traces showing the tree graph:
        treegraph_go_data = plotly_treegraph_data(tree, legendgroup='tree', legendgrouptitle={'text': 'TreeGraph'})
        go_data.extend(treegraph_go_data)
        task_traces.extend(["TreeGraph"] * len(treegraph_go_data))
    # Create the traces for "FruitDirection" & "StemDirection" data if it exists:
    if api_data['hasAnglesAndInternodes']:
        print("Creating Plotly representation of 'FruitDirection' & 'StemDirection'...")
        # fruit_dir = get_task_data(dataset_id, "AnglesAndInternodes", 'fruit_direction.json', **api_kwargs)
        # stem_dir = get_task_data(dataset_id, "AnglesAndInternodes", 'stem_direction.json', **api_kwargs)
        fruit_dir = data_dict["FruitDirection"]
        stem_dir = data_dict["StemDirection"]
        # Create the list of traces showing the fruit directions:
        fruit_dir_go_data = plotly_direction_data(fruit_dir["fruit_dirs"], fruit_dir["bp_coords"], "fruit",
                                                  legendgroup='fruit',
                                                  legendgrouptitle={'text': 'FruitDirection'})
        go_data.extend(fruit_dir_go_data)
        task_traces.extend(["FruitDirection"] * len(fruit_dir_go_data))
        # Create the list of traces showing the stem directions:
        stem_dir_go_data = plotly_direction_data(stem_dir["stem_dirs"], stem_dir["bp_coords"], "stem",
                                                 legendgroup='stem',
                                                 legendgrouptitle={'text': 'StemDirection'})
        go_data.extend(stem_dir_go_data)
        task_traces.extend(["StemDirection"] * len(stem_dir_go_data))
        # Create the list of traces showing the selected/hover fruits:
        big_fruits = plotly_direction_data(fruit_dir["fruit_dirs"], fruit_dir["bp_coords"], "big fruit",
                                           line_kwargs={"width": 25}, showlegend=False)
        go_data.extend(big_fruits)
        hover_traces = [f"BigFruit_{f}" for f in range(len(big_fruits))]

    # Get pcd points and mesh vertices to get axes range and ratio:
    pcd = np.array(data_dict["PointCloud"])
    if api_data['hasTriangleMesh']:
        mesh_vertices = np.array(data_dict["TriangleMesh"]["vertices"])
    else:
        mesh_vertices = None
    # Get axes range:
    mini, maxi = get_global_range(pcd, mesh_vertices)
    x_range = [mini[0], maxi[0]]
    y_range = [mini[1], maxi[1]]
    z_range = [mini[2], maxi[2]]
    # Get axes ratio:
    range_arr = np.array([x_range, y_range, z_range])
    axes_ratio = get_axes_ratio(range_arr[:, 0], range_arr[:, 1])

    # Create the Plotly figure:
    fig = go.Figure(data=go_data)
    # Update the scene using axes range & aspec ratio:
    fig.update_scenes(aspectmode='manual',
                      xaxis={'range': x_range}, aspectratio_x=axes_ratio[0],
                      yaxis={'range': y_range}, aspectratio_y=axes_ratio[1],
                      zaxis={'range': z_range}, aspectratio_z=axes_ratio[2])
    # Update the layout:
    fig.update_layout(uirevision='constant', font_family=FONT_FAMILY,
                      # paper_bgcolor="#F3F3F3",
                      margin={'t': 25, 'b': 5}, autosize=True)
    # At first, we only display the "PointCloud" trace:
    update_trace_visibility(["PointCloud"], fig, task_traces)
    return fig, task_traces, hover_traces, False


@callback(Output('n-fruits', 'data'),
          Input('hover-traces', 'data'),
          prevent_initial_call=True)
def store_n_fruits(hover_traces):
    """Store the number of fruits found in the 'FruitDirection' dict entry of the stored 'data-dict' data."""
    print(f"[{t_now()}] Callback `store_n_fruits`...")
    if hover_traces is not None:
        return len(hover_traces)
    else:
        return 0


@callback(Output('fruit-slider', 'min'),
          Output('fruit-slider', 'max'),
          Output('fruit-slider', 'value'),
          Output('fruit-slider', 'marks'),
          Output('fruit-slider', 'disabled'),
          Input('n-fruits', 'data'),
          prevent_initial_call=True)
def init_fruit_slider(n_fruits):
    """Initialize the 'fruit-slider' component properties based on the stored 'n-fruits' data.
    
    Parameters
    ----------
    n_fruits : int
        Total number of fruits.
    """
    print(f"[{t_now()}] Callback `init_fruit_slider`...")
    if n_fruits == 0:
        fruits_range = {-1: "", 0: ""}
        return -1, 0, [-1, 0], fruits_range, True
    else:
        fruits_range = {-1: "root"} | {f: f"{f}" for f in range(n_fruits)}
        return -1, n_fruits - 1, [-1, n_fruits - 1], fruits_range, False


@callback(Output('3d-viewer-graph', 'figure', allow_duplicate=True),
          Input('task-data-checklist', 'value'),
          State('3d-viewer-graph', 'figure'),
          State('task-traces', 'data'),
          prevent_initial_call=True)
def update_trace_visibility(task_checklist, figure, task_traces):
    """Callback displaying the task traces depending on selected tasks.
    
    Parameters
    ----------
    task_checklist : list
        List of selected tasks from 'task-data-checklist' checkboxes.
    figure : dict
        The 'figure' component from '3d-viewer-graph' container.
        A dictionary of plotly figure properties.
    task_traces : list
        The stored list of task's traces.
    """
    print(f"[{t_now()}] Callback `update_trace_visibility`...")
    if figure is None:
        print("Empty figure!")
        return go.Figure()

    n_tasks = len(task_traces)
    for n, trace in enumerate(figure['data'][:n_tasks]):
        trace['visible'] = task_traces[n] in task_checklist

    return figure


@callback(Output('selected-fruits', 'data'),
          Input('sequences-graph', 'hoverData'),
          Input('sequences-graph', 'selectedData'),
          prevent_initial_call=True)
def store_selected_fruits(hover_data, selected_data):
    """Store the list of selected fruits to render."""
    if selected_data is not None:
        hover_data = selected_data

    if hover_data is not None:
        fruit_idx = hover_data['points'][0]['pointIndex']
        sel_fruit_idx = list(range(fruit_idx, fruit_idx + 2))
    else:
        sel_fruit_idx = None

    return sel_fruit_idx


@callback(Output('3d-viewer-graph', 'figure', allow_duplicate=True),
          Input('selected-fruits', 'data'),
          State('3d-viewer-graph', 'figure'),
          State('task-traces', 'data'),
          State('hover-traces', 'data'),
          prevent_initial_call=True)
def update_selected_fruits(sel_fruit_idx, figure, task_traces, hover_traces):
    """Highlight the selected fruits on the 3D viewer figure."""
    print(f"[{t_now()}] Callback `update_selected_fruits`...")
    if figure is None:
        print("Empty figure!")
        return go.Figure()

    if sel_fruit_idx is None:
        sel_fruit_traces = []
    else:
        sel_fruit_traces = [f"BigFruit_{f}" for f in sel_fruit_idx]

    n_tasks = len(task_traces)
    for n, trace in enumerate(figure['data'][n_tasks:]):
        trace['visible'] = hover_traces[n] in sel_fruit_traces

    return figure


@callback(Output('3d-viewer-graph', 'figure', allow_duplicate=True),
          Input('fruit-slider', 'value'),
          State('3d-viewer-graph', 'figure'),
          State('fruit-slider', 'min'),
          State('fruit-slider', 'max'),
          State('data-dict', 'data'),
          State('data-range', 'data'),
          prevent_initial_call=True)
def update_3d_viewer_range(fruit_range, fig, fs_mini, fs_maxi, data_dict, data_range):
    """Update the 3D viewer axes range depending on selected fruit interval."""
    print(f"[{t_now()}] Callback `update_3d_viewer_range`...")
    if fig is None:
        print("Empty figure!")
        return go.Figure()

    mini, maxi = data_range
    x_range = [mini[0], maxi[0]]
    y_range = [mini[1], maxi[1]]
    z_range = [mini[2], maxi[2]]
    if fruit_range is not None and fruit_range != [fs_mini, fs_maxi]:
        bp_coords = data_dict["FruitDirection"]["bp_coords"]
        f_low, f_high = fruit_range
        if f_low == fs_mini:
            z_range[0] = mini[2]
        else:
            f_low_coord = bp_coords[str(f_low)][2]
            z_range[0] = f_low_coord * 1.05 if f_low_coord < 0 else f_low_coord * 0.95
        if f_high == fs_maxi:
            z_range[1] = maxi[2]
        else:
            f_high_coord = bp_coords[str(f_high)][2]
            z_range[1] = f_high_coord * 1.05 if f_high_coord > 0 else f_high_coord * 0.95

    range_arr = np.array([x_range, y_range, z_range])
    axes_ratio = get_axes_ratio(range_arr[:, 0], range_arr[:, 1])
    # Update the scene using axes range & aspec ratio:
    fig['layout']["scene"]["aspectmode"] = 'manual'
    fig['layout']["scene"]["aspectratio"] = {"x": axes_ratio[0], "y": axes_ratio[1], "z": axes_ratio[2]}
    fig['layout']["scene"]["xaxis"]['range'] = x_range
    fig['layout']["scene"]["yaxis"]['range'] = y_range
    fig['layout']["scene"]["zaxis"]['range'] = z_range

    return fig


@callback(Output("fruit-slider", "value", allow_duplicate=True),
          State("fruit-slider", "min"),
          State("fruit-slider", "max"),
          State("fruit-slider", "value"),
          Input("fruit-slider-up", 'n_clicks'),
          Input("fruit-slider-down", 'n_clicks'),
          prevent_initial_call=True)
def update_fruit_slider_range(mini, maxi, range, up, down):
    """Update the fruit slider values when using the UP/Down arrows."""
    print(f"[{t_now()}] Callback `update_fruit_slider`...")
    if "fruit-slider-up" == ctx.triggered_id:
        if range[1] < maxi:
            return [range[0] + 1, range[1] + 1]
    elif "fruit-slider-down" == ctx.triggered_id:
        if range[0] > mini:
            return [range[0] - 1, range[1] - 1]
    else:
        return range


@callback(Output("sequences-graph", "figure"),
          Input("y-axis-dropdown", "value"),
          State('dataset-id', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'))
def create_sequence_graph(y_axis, dataset_id, host, port):
    """Create the sequence graph figure."""
    print(f"[{t_now()}] Callback `update_sequence_graph`...")
    api_kwargs = {"host": host, "port": port}
    from plantdb.rest_api_client import get_angles_and_internodes_data
    measures = get_angles_and_internodes_data(dataset_id, **api_kwargs)
    # Returns an empty figure if no measure could be loaded from the API:
    if measures is None:
        return go.Figure()

    # Edit the Y-axis representation depending on dropdown selection:
    if y_axis == 'distance':
        vert_axis = np.cumsum(measures['internodes'])
        y_axis_label = "Cumulative internode distances (mm)."
    else:
        vert_axis = None
        y_axis_label = "Interval index"

    # Create the Plotly figure:
    seq_fig = plotly_vert_sequences(measures, vert_axis, y_axis_label, marker_kwargs={'size': 10})
    seq_fig.update_layout(uirevision='value', font_family=FONT_FAMILY,
                          # paper_bgcolor="#F3F3F3",
                          margin={'t': 25, 'b': 5}, autosize=True)
    return seq_fig
