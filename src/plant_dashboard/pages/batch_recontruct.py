#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from base64 import b64decode
from base64 import b64encode

import dash_ace
import dash_bootstrap_components as dbc
import toml
from dash import Input
from dash import Output
from dash import State
from dash import callback
from dash import dcc
from dash import get_asset_url
from dash import html
from dash import register_page

from plant3dvision.utils import tasks_graph_from_cfg
from plant3dvision.visu import draw_left_to_right
from plant3dvision.webui.utils import config_upload

register_page(__name__, path_template="/batch_reconstruct")

# The card regrouping the reconstruction configuration parameters:
batch_configuration_card = [
    dbc.Card(
        id="batch-configuration-card",
        children=[
            dbc.CardHeader("Configuration"),
            dbc.CardBody([
                dash_ace.DashAceEditor(
                    id='batch-reconstruct-cfg-toml',
                    value=toml.dumps(toml.load(get_asset_url('geom_pipe_real.toml')[1:])),
                    mode='toml',
                    theme='tomorrow',
                    tabSize=2,
                    setOptions={
                        'fontSize': '13pt'
                    },
                    enableLiveAutocompletion=True,
                    enableBasicAutocompletion=True,
                    placeholder="Reconstruction configuration (TOML).",
                    style={'width': 'auto', 'height': '100%'},
                    debounceChangePeriod=2000),
            ], style={'height': "65vh", 'min-height': '500px', 'width': 'auto'}
            ),
            dbc.CardFooter([
                config_upload(),
            ], style={"align-content": 'center'})
        ]
    )
]

# A card to display the tasks dependency graph:
batch_task_graph_card = [
    dbc.Card(
        id="batch-task-graph-card",
        children=[
            dbc.CardHeader("Tasks dependency graph"),
            dbc.CardBody([
                html.Div([
                    html.Img(src="", alt="Tasks dependency graph.", id='batch-task-graph-img')
                ], style={
                    'width': 'auto',  # Auto sizing with the parent container
                    'overflowX': 'auto',  # Enable horizontal scrolling
                    'whiteSpace': 'nowrap'  # Prevent line breaks
                })
            ])
        ]
    )
]

batch_select_card = [
    dbc.Card(
        id="batch-select-card",
        children=[
            dbc.CardHeader("Dataset selection"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="bi bi-regex")),
                            dbc.Input(id="dataset-query", placeholder="Search query"),
                        ])
                    ], md=4, className="mb-3", ),
                    dbc.Col([
                        html.Div([
                            dbc.Button([html.I(className="bi bi-search me-2"), "Search"],
                                       id="run-search-button", outline=True, color="primary")
                        ]),
                    ], md=2),
                    dbc.Col([
                        dcc.Markdown(id="dataset-query-response",
                                     children='_Run a search..._'),
                    ], md=6, align="center"),
                ]),
                dbc.FormText(
                    "Use regexp patterns like '.*' to select several dataset to reconstruct.",
                    color="secondary",
                ),
            ]),
            dbc.CardFooter([
                dbc.Button([html.I(className="bi bi-list-check me-2"), "Match list"],
                           id="open-match-list", color='secondary', outline=True),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Match list:")),
                        dbc.ModalBody(children=[
                            dcc.Markdown(id="dataset-query-output",
                                         children="_Run a search to get the list of matching dataset..._"), ]),
                    ],
                    id="match-list-modal", size='md', scrollable=True,
                )
            ], style={"align-content": 'center'}),
        ]
    )
]

# The card regrouping the buttons to reconstruct and upload:
batch_analysis_card = [
    dbc.Card(
        id="batch-analysis-card",
        children=[
            dbc.CardHeader("Batch analysis"),
            dbc.CardBody([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Choose a task:"),
                            dcc.Dropdown([''], '', id='batch-task-dropdown', persistence=True),
                        ], md=6),
                        dbc.Col(
                            [
                                dbc.Label("Choose a type of reconstruction:"),
                                dbc.RadioItems(
                                    options=[
                                        {"label": "Avoid", "value": "avoid"},
                                        {"label": "Append", "value": "append"},
                                        {"label": "Clean", "value": "clean"},
                                    ],
                                    id="batch-reconstruct-type-input",
                                    value="avoid", inline=True,
                                ),
                            ], md=6,
                        )
                    ]),
                    html.Br(),
                    dbc.Button([html.I(className="bi bi-play-circle me-2"), 'Start reconstruction'],
                               id='batch-reconstruct-button',
                               outline=True, color="primary", disabled=True),
                    html.Br(),
                    dcc.Markdown(id='batch-reconstruct-response', children="_Run a reconstruction first..._"),
                ])
            ]),
            dbc.CardFooter([
                dbc.Button([html.I(className="bi bi-hourglass-split me-2"), "Open jobs queue"],
                           id="open-job queue", href="/job_queue",
                           color='secondary', outline=True),
            ], style={"align-content": 'center'}),
        ]
    )
]

layout = html.Div([
    # Store the dataset id to use in the callback.
    dcc.Store(id='batch-cfg-dict', data={}),
    dcc.Store(id='batch-task-graph-root', data=None),
    dcc.Store(id='batch-task-graph-leaves', data=None),
    # Content of the reconstruction app:
    dbc.Row(
        id="batch-app-content",
        children=[
            dbc.Col(batch_configuration_card, md=6),
            dbc.Col(batch_task_graph_card + [html.Br()] + batch_select_card + [html.Br()] + batch_analysis_card, md=6)
        ],
    ),
])


@callback(Output('batch-reconstruct-cfg-toml', 'value'),
          Input('url', 'pathname'),
          Input('cfg-upload', 'contents'))
def init_reconstruct_cfg(pathname, contents):
    """Initialize the reconstruction config."""
    if contents is not None:
        # Update the contents of the TOML configuration file when uploading a configuration file:
        content_type, content_string = contents.split(',')
        cfg = b64decode(content_string)
        return cfg.decode()
    else:
        # Load the default TOML asset:
        cfg = toml.load(get_asset_url('geom_pipe_real.toml')[1:])
        return toml.dumps(cfg)


@callback(Output('batch-cfg-dict', 'data'),
          Input('batch-reconstruct-cfg-toml', 'value'),
          State('batch-cfg-dict', 'data'),
          prevent_initial_call=True)
def update_cfg(cfg_str, current_cfg):
    """Get the contents of the TOML configuration file and return it to the text area."""
    try:
        cfg = toml.loads(cfg_str)
    except toml.TomlDecodeError:
        return current_cfg
    else:
        return cfg


@callback(Output('batch-task-dropdown', 'options'),
          Output('batch-task-dropdown', 'value'),
          Input('batch-cfg-dict', 'data'),
          prevent_initial_call=True)
def update_tasks_dropdown(cfg_dict):
    """Update the list of tasks available in the dropdown when editing the configuration."""
    g_task, root, leaves = tasks_graph_from_cfg(cfg_dict)
    tasks_list = list(g_task.nodes)
    return tasks_list, leaves[-1]


@callback(Output('batch-task-graph-img', 'src'),
          Output('batch-task-graph-root', 'data'),
          Output('batch-task-graph-leaves', 'data'),
          Input('batch-cfg-dict', 'data'))
def update_task_graph_img(cfg_dict):
    """Update the tasks dependency graph SVG image."""
    g_task, root, leaves = tasks_graph_from_cfg(cfg_dict)
    [g_task.remove_node(r) for r in root]
    svg_string = draw_left_to_right(g_task)
    img_src = f"data:image/svg+xml;base64,{b64encode(svg_string.encode()).decode()}"
    return img_src, root, leaves


@callback(Output('dataset-query-response', 'children'),
          Output('dataset-query-output', 'children'),
          Output('batch-dataset-ids', 'data'),
          Output('batch-reconstruct-button', 'disabled'),
          Input('run-search-button', 'n_clicks'),
          State('dataset-query', 'value'),
          State('dataset-dict', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          prevent_initial_call=True)
def batch_select_dataset(n_clicks, query_pattern, dataset_dict, host, port):
    if query_pattern is None:
        msg = "Enter a valid query pattern!\nTo select all dataset, use '`.+`'."
        return msg, msg, [], True
    if dataset_dict is None:
        from plant3dvision.webui.utils import get_dataset_dict
        try:
            dataset_dict = get_dataset_dict(host, port)
        except Exception as e:
            response_msg = "Failed accessing the PlantDB!"
            log_output_msg = "Check the PlantDB REST API (configuration)[/plantdb_api]!"
            return response_msg, log_output_msg, None, True

    # List to store matching strings
    selected_dataset = []
    for dataset_name in dataset_dict.keys():
        if re.search(query_pattern, dataset_name):
            selected_dataset.append(dataset_name)
    n = len(selected_dataset)
    selected_dataset = sorted(selected_dataset)
    md_matched = f"Found {n} matching dataset:" + "\n  - " + "\n  - ".join([f"`{ds}`" for ds in selected_dataset])
    disable_reconstruct_button = False if len(selected_dataset) > 1 else True
    return f"Found {n} matching dataset!", md_matched, selected_dataset, disable_reconstruct_button


# Open/Close the reconstruction logger modal:
@callback(
    Output("match-list-modal", "is_open"),
    Input("open-match-list", "n_clicks"),
    State("match-list-modal", "is_open"),
)
def toggle_match_list_modal(n, is_open):
    if n:
        return not is_open
    return is_open


@callback(Output('batch-reconstruct-response', 'children'),
          Input('batch-reconstruct-button', 'n_clicks'),
          State('batch-task-dropdown', 'value'),
          State('batch-reconstruct-cfg-toml', 'value'),
          State('batch-dataset-ids', 'data'),
          State('batch-reconstruct-type-input', 'value'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          prevent_initial_call=True)
def batch_reconstruct(n_clicks, task, cfg, dataset_list, reconstruct_type, host, port):
    from plant3dvision.webui.celery_app import task_run_reconstruct
    from plantdb.rest_api_client import get_reconstruction_config

    if len(dataset_list) == 0:
        return "No dataset selected!"

    sel_dataset = []
    for dataset_id in dataset_list:
        # Try to load an existing reconstruction configuration:
        api_kwargs = {"host": host, "port": port}
        old_cfg = get_reconstruction_config(dataset_id, cfg_fname='pipeline.toml', **api_kwargs)
        # Check if dataset is already reconstructed (has a `pipeline.toml` file):
        if reconstruct_type == "avoid":
            if old_cfg is not None:
                print(f"Skipping reconstruction of dataset `{dataset_id}` as it is already reconstructed!")
                continue  # skip this dataset
        sel_dataset.append(dataset_id)
        if reconstruct_type == "clean" and old_cfg is not None:
            new_reconstruct = True
        else:
            new_reconstruct = False
        print(f"Queuing {'new ' if new_reconstruct else ''}reconstruction of dataset `{dataset_id}`.")
        task_run_reconstruct.delay(dataset_id, task, cfg, new_reconstruct, host, port)

    if len(sel_dataset) == 0:
        return "**No job submitted!** All dataset have been avoided as they all had a `pipeline.toml` file."
    else:
        return f"Started `{task}` task on {len(sel_dataset)} dataset:", ",".join(sel_dataset)
