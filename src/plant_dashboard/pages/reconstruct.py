#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from base64 import b64decode
from base64 import b64encode
from logging import getLogger

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
from dash_cool_components import KeyedFileBrowser

from plant3dvision.utils import tasks_graph_from_cfg
from plant3dvision.visu import draw_left_to_right
from plant3dvision.webui.utils import compare_lib_version
from plant3dvision.webui.utils import config_upload
from plant3dvision.webui.utils import import_dataset_archive
from plant3dvision.webui.utils import read_log
from plant3dvision.webui.utils import refresh_dataset
from plant3dvision.webui.utils import run_reconstruct
from plant3dvision.webui.utils import temp_scan_dir
from plantdb.rest_api_client import get_reconstruction_config
from romitask.log import get_log_filename

register_page(__name__, path_template="/reconstruct/<dataset_id>")

# - MODALS:
# Modal to display the upload log, open with button 'open-reconstruct-log':
reconstruct_log_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Reconstruction log")),
        dbc.ModalBody(children=[
            dcc.Markdown(id="reconstruct-output", children="_Run a reconstruction first..._", style={
                'width': 'auto',  # Auto sizing with the parent container
                'overflowX': 'auto',  # Enable horizontal scrolling
                'whiteSpace': 'nowrap'  # Prevent line breaks
            }),
        ]),
    ],
    id="reconstruct-modal", fullscreen=True, scrollable=True,
)

# Modal to display the upload log, open with button 'open-upload-log':
upload_log_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Local dataset log")),
        dbc.ModalBody(children=[
            dcc.Markdown(id="upload-output", children="_Upload first..._"),
        ], style={
            'width': 'auto',  # Auto sizing with the parent container
            'overflowX': 'auto',  # Enable horizontal scrolling
            'whiteSpace': 'nowrap'  # Prevent line breaks
        }),
    ],
    id="upload-modal", fullscreen=True, scrollable=True,
)

# Modal automatically opening when loading a dataset that is already reconstructed:
reconstruct_warning_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Warning")),
    dbc.ModalBody([
        dbc.Alert(
            [
                html.I(className="bi bi-exclamation-diamond me-2"),
                "This dataset is already reconstructed!",
            ],
            color="warning",
            className="d-flex align-items-center",
        ),
        dbc.Alert(
            [
                html.I(className="bi bi-info-circle me-2"),
                "The previous reconstruction configuration has been loaded.",
            ],
            color="info",
            className="d-flex align-items-center",
        ),
        "Libraries version comparison table:",
        dbc.Placeholder(id='version-table'),
        html.Br(),
        dbc.Row([
            dbc.Col([
                dbc.Button('Start new reconstruction',
                           id='new-reconstruct-button',
                           color="primary"),
                dbc.Tooltip("This will clean the dataset prior to reconstruction.",
                            target='new-reconstruct-button', placement='top')
            ], md=6, class_name="d-grid gap-2"),
            dbc.Col([
                dbc.Button('Append reconstruction',
                           id='append-reconstruct-button',
                           color="primary"),
                dbc.Tooltip("This will keep the dataset as is, and run the reconstruction.",
                            target='append-reconstruct-button', placement='top')
            ], md=6, class_name="d-grid gap-2"),
        ])
    ]),
],
    id="reconstruct-warning-modal", size="lg", scrollable=True, is_open=False, backdrop='static',
)

# Modal to browser local dataset files, open with `explore-button` button:
file_browser_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("File browser")),
    dbc.ModalBody(children=[
        KeyedFileBrowser(
            id='local-file-browser',
            files=[],
        )
    ])
],
    id="file-browser-modal", size="lg", scrollable=True, is_open=False,
)

# - CARDS LAYOUT:
# A card to display the TOML reconstruction configuration to use  when starting a reconstruction:
configuration_card = [
    dbc.Card(
        id="configuration-card",
        children=[
            dbc.CardHeader("Configuration"),
            dbc.CardBody([
                dash_ace.DashAceEditor(
                    id='reconstruct-cfg-toml',
                    value='# Enter your TOML here\n[section]\nkey = "value"',
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
task_graph_card = [
    dbc.Card(
        id="task-graph-card",
        children=[
            dbc.CardHeader("Tasks dependency graph"),
            dbc.CardBody([
                html.Div([
                    html.Img(src="", alt="Tasks dependency graph.", id='task-graph-img')
                ], style={
                    'width': 'auto',  # Auto sizing with the parent container
                    'overflowX': 'auto',  # Enable horizontal scrolling
                    'whiteSpace': 'nowrap'  # Prevent line breaks
                })
            ])
        ]
    )
]

# A card regrouping the buttons to start/cancel reconstruction and open the log:
analysis_card = [
    dbc.Card(
        id="analysis-card",
        children=[
            dbc.CardHeader("Analysis"),
            dbc.CardBody([
                dcc.Dropdown([''], '', id='task-dropdown', persistence=True),
                html.Br(),
                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-play-circle me-2"), 'Start reconstruction'],
                                   id='start-reconstruct-button',
                                   outline=True, color="primary"),
                    ]),
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-stop-circle me-2"), 'Cancel reconstruction'],
                                   id='cancel-reconstruct-button',
                                   outline=True, color="primary", disabled=True),
                    ]),
                ]),
                html.Br(),
                dcc.Markdown(id='reconstruct-response', children="_Run a reconstruction first..._"),
            ]),
            dbc.CardFooter([
                dbc.Button([html.I(className="bi bi-journal-text me-2"), "Open log"],
                           id="open-reconstruct-log",
                           color='secondary', outline=True),
                reconstruct_log_modal
            ], style={"align-content": 'center'}),
        ]
    )
]

# Car to upload acquired dataset to PlantDB REST API.
local_dataset_card = [
    dbc.Card(
        id="local-dataset-card",
        children=[
            dbc.CardHeader("Local dataset"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-folder me-2"), 'Explore'],
                                   id='explore-button',
                                   outline=True, color="primary", disabled=True),
                    ]),
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-upload me-2"), 'Upload'],
                                   id='upload-button', n_clicks=0,
                                   outline=True, color="primary", disabled=True),
                    ]),
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-arrow-counterclockwise me-2"), 'Clean'],
                                   id='clean-button',
                                   outline=True, color="primary", disabled=True),
                    ]),
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-trash3 me-2"), 'Remove'],
                                   id='remove-button',
                                   outline=True, color="primary", disabled=True)
                    ])
                ]),
                html.Br(),
                dcc.Markdown(id='upload-response', children="_Upload first..._"),
            ]),
            dbc.CardFooter([
                dbc.Button([html.I(className="bi bi-journal-text me-2"), "Open log"],
                           id="open-upload-log",
                           color='secondary', outline=True),
                upload_log_modal,
            ], style={"align-content": 'center'})
        ]
    )
]


def layout(dataset_id=None, **kwargs):
    """Create the page layout for the reconstruction page.

    Parameters
    ----------
    dataset_id : str
        The name of the dataset to show in the reconstruction page.

    Returns
    -------
    html.Div
        The layout for the reconstruction page.
    """
    return html.Div([
        # Store the dataset id to use in the callback.
        dcc.Store(id='dataset-id', data=dataset_id),
        dcc.Store(id='cfg-dict', data={}),
        dcc.Store(id='libraries-table', data=None),
        dcc.Store(id='task-graph-root', data=None),
        dcc.Store(id='task-graph-leaves', data=None),
        dcc.Store(id='is-reconstructed', data=False),
        dcc.Store(id='new-reconstruct', data=False),
        # Content of the reconstruction app:
        dbc.Row(
            id="app-content",
            children=[
                reconstruct_warning_modal,
                file_browser_modal,
                dbc.Col(configuration_card, md=6,
                        style={'min-width': '500px'}),
                dbc.Col(task_graph_card + [html.Br()] + analysis_card + [html.Br()] + local_dataset_card, md=6,
                        style={'min-width': '500px'})
            ],
        ),
    ])


@callback(Output('reconstruct-cfg-toml', 'value'),
          Output('libraries-table', 'data'),
          Output('is-reconstructed', 'data'),
          Input('dataset-id', 'data'),
          State('libraries-version', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'))
def init_reconstruct_cfg(dataset_id, libraries_version, host, port):
    """Initialize the reconstruction config."""
    # Try to load an existing reconstruction configuration:
    api_kwargs = {"host": host, "port": port}
    cfg = get_reconstruction_config(dataset_id, cfg_fname='pipeline.toml', **api_kwargs)
    # If no reconstruction configuration found, load the default TOML asset:
    if cfg is None:
        cfg = toml.load(get_asset_url('geom_pipe_real.toml')[1:])
        return toml.dumps(cfg), None, False
    else:
        df = compare_lib_version(cfg, libraries_version)
        return toml.dumps(cfg), df.to_json(), True


@callback(Output('reconstruct-warning-modal', 'is_open'),
          Output('version-table', 'children'),
          Input('libraries-table', 'data'))
def version_table(lib_table):
    """Create the libraries version comparison table"""
    import pandas as pd
    from io import StringIO
    if lib_table is None:
        return False, None
    else:
        df = pd.read_json(StringIO(lib_table))
        return True, dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, index=True)


@callback(Output('new-reconstruct', 'data'),
          Output('reconstruct-warning-modal', 'is_open', allow_duplicate=True),
          Input('new-reconstruct-button', 'n_clicks'),
          Input('append-reconstruct-button', 'n_clicks'),
          prevent_initial_call=True)
def store_reconstruct_type(new_click, append_click):
    if new_click:
        return True, False
    else:
        return False, False


@callback(Output('reconstruct-cfg-toml', 'value', allow_duplicate=True),
          Input('cfg-upload', 'contents'),
          prevent_initial_call=True)
def upload_cfg(contents):
    if contents is not None:
        # Update the contents of the TOML configuration file when uploading a configuration file:
        content_type, content_string = contents.split(',')
        cfg = b64decode(content_string)
        return cfg.decode()


@callback(Output('cfg-dict', 'data'),
          Input('reconstruct-cfg-toml', 'value'),
          State('cfg-dict', 'data'),
          prevent_initial_call=True)
def update_cfg(cfg_str, current_cfg):
    """Get the contents of the TOML configuration file and return it to the text area."""
    try:
        cfg = toml.loads(cfg_str)
    except toml.TomlDecodeError:
        return current_cfg
    else:
        return cfg


@callback(Output('task-dropdown', 'options'),
          Output('task-dropdown', 'value'),
          Input('cfg-dict', 'data'),
          prevent_initial_call=True)
def update_tasks_dropdown(cfg_dict):
    """Update the list of tasks available in the dropdown when editing the configuration."""
    g_task, root, leaves = tasks_graph_from_cfg(cfg_dict)
    tasks_list = list(g_task.nodes)
    return tasks_list, leaves[-1]


@callback(Output('task-graph-img', 'src'),
          Output('task-graph-root', 'data'),
          Output('task-graph-leaves', 'data'),
          Input('cfg-dict', 'data'))
def update_task_graph_img(cfg_dict):
    """Update the tasks dependency graph SVG image."""
    g_task, root, leaves = tasks_graph_from_cfg(cfg_dict)
    [g_task.remove_node(r) for r in root]
    svg_string = draw_left_to_right(g_task)
    img_src = f"data:image/svg+xml;base64,{b64encode(svg_string.encode()).decode()}"
    return img_src, root, leaves


@callback(Output('start-reconstruct-button', 'disabled', allow_duplicate=True),
          Input('task-dropdown', 'value'),
          prevent_initial_call=True)
def enable_reconstruct_button(task):
    """Enable reconstruct button if changing the task in the dropdown."""
    return False


# Callback of the "open-reconstruct-log" button:
@callback(Output("reconstruct-modal", "is_open"),
          Input("open-reconstruct-log", "n_clicks"),
          State("reconstruct-modal", "is_open"),
          )
def toggle_reconstruct_log_modal(n, is_open):
    """Open/Close the reconstruction logger modal."""
    if n:
        return not is_open
    return is_open


# Callback of the "open-upload-log" button:
@callback(Output("upload-modal", "is_open"),
          Input("open-upload-log", "n_clicks"),
          State("upload-modal", "is_open"),
          )
def toggle_upload_log_modal(n, is_open):
    """Open/Close the upload logger modal."""
    if n:
        return not is_open
    return is_open


# Callback of the 'upload-button' button:
@callback(Output('upload-response', 'children', allow_duplicate=True),
          Output('upload-output', 'children', allow_duplicate=True),
          Input('upload-button', 'n_clicks'),
          State('dataset-id', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          running=[
              (Output('upload-button', 'disabled'), True, False),
              (Output('upload-button', 'children'),
               [dbc.Spinner(size="sm"), " Uploading..."],
               [html.I(className="bi bi-check me-2"), "Uploaded"]),
          ],
          prevent_initial_call=True)
def upload_local_dataset(n_clicks, dataset_id, host, port):
    """Upload the local dataset temporary directory as an archive to the served PlantDB."""
    from plant3dvision.webui.utils import upload_dataset
    if n_clicks > 0:
        log_msg, files = upload_dataset(dataset_id, host, port)
        files = f"The following {len(files)} files were uploaded:" + "".join([f"\n - `{f}`" for f in files])
    else:
        log_msg, files = "Click the 'Upload' button first!", ""

    # Call a refresh on this dataset as new filesets & files are now available:
    _ = refresh_dataset(dataset_id, host, port)
    return log_msg, files


# Callback of the "remove-button" button:
@callback(Output('upload-response', 'children', allow_duplicate=True),
          Input('remove-button', 'n_clicks'),
          State('dataset-id', 'data'),
          running=[
              (Output('remove-button', 'disabled'), True, False),
              (Output('remove-button', 'children'),
               [dbc.Spinner(size="sm"), " Removing..."],
               [html.I(className="bi bi-check me-2"), "Removed"]),
          ],
          prevent_initial_call=True)
def remove_temp_scan_dir(n_clicks, dataset_id):
    """Remove the local dataset temporary directory."""
    dataset_path = temp_scan_dir(dataset_id)
    shutil.rmtree(dataset_path)
    return f"Removed the temporary copy of `{dataset_id}` dataset!"


# Callback of the "clean-button" button:
@callback(Output('start-reconstruct-button', 'disabled', allow_duplicate=True),
          Output('clean-button', 'disabled', allow_duplicate=True),
          Output('upload-response', 'children', allow_duplicate=True),
          Output('upload-output', 'children', allow_duplicate=True),
          Input('clean-button', 'n_clicks'),
          State('dataset-id', 'data'),
          running=[
              (Output('clean-button', 'disabled'), True, False),
              (Output('clean-button', 'children'),
               [dbc.Spinner(size="sm"), " Cleaning..."],
               [html.I(className="bi bi-check me-2"), "Cleaned"]),
          ],
          prevent_initial_call=True)
def clean_temp_scan_dir(n_clicks, dataset_id):
    """Execute the Clean task on the local dataset temporary directory."""
    from romitask.cli.romi_run_task import run_task
    dataset_path = temp_scan_dir(dataset_id)
    # Cleanup potential lock file:
    lock_fpath = dataset_path.parent / 'lock'
    if lock_fpath.exists():
        lock_fpath.unlink()
    # Create a combined logger using the configuration:
    logger = getLogger('clean')
    log_fname = get_log_filename('Clean')

    # Execute the "Clean" task:
    success = False
    try:
        run_task(dataset_path, task='Clean', config={"Clean": {'no_confirm': True}}, logger=logger, log_fname=log_fname)
        success = True
    except Exception as e:
        logger.error(e)

    # Read the log and format it to use in a markdown container:
    log = "```\n" + f"{read_log(dataset_path / log_fname)}```"

    if success:
        return False, True, f"Task `Clean` performed **successfully** on dataset _{dataset_id}_ !", log
    else:
        return False, False, f"Task `Clean` **failed**, have look at the log!", log


@callback(Output('remove-button', 'disabled'),
          Output('clean-button', 'disabled'),
          Output('upload-response', 'children'),
          Output('upload-output', 'children'),
          Output('explore-button', 'disabled'),
          Output('upload-button', 'disabled'),
          Input('url', 'pathname'),
          State('dataset-id', 'data'))
def check_temp_scan_dir(url, dataset_id):
    """Check the presence of a temporary local copy.

    Parameters
    ----------
    url : str
        The page URL, only triggers the check if the URL is for a reconstruct page.
    dataset_id : str
        The dataset ID.

    Returns
    -------
    bool
        The `disabled` state of the 'remove-button' button.
    str
        The short response displayed on the page in the `dash.dcc.markdown` element 'upload-response'.
    str
        The detailed log output displayed in the `dash_bootstrap_components.modal` element 'upload-output'.
    """
    from plant3dvision.webui.utils import _reconstruct_href
    if url == _reconstruct_href(dataset_id):
        dataset_path = temp_scan_dir(dataset_id)
        if dataset_path.is_dir():
            list_dir = sorted(dataset_path.iterdir())
            l_folders = [i for i in list_dir if i.is_dir()]
            l_files = [i for i in list_dir if i.is_file()]
            if len(list_dir) == 0:
                shutil.rmtree(dataset_path)
                log_summary = f"Found an empty local copy `{dataset_id}` dataset, removed it!"
                return True, True, log_summary, log_summary, False, True
            else:
                log_summary = f"Found a local copy of `{dataset_id}` dataset with {len(l_folders)} folders."
                folders_list = "\n   - " + "\n   - ".join(f"`{f.name}{'/'}`" for f in l_folders)
                folders_list += "\n   - " + "\n   - ".join(f"`{f.name}`" for f in l_files)
                log_detail = f"Found a local copy of `{dataset_id}` dataset with the following folders:{folders_list}"
                return False, False, log_summary, log_detail, False, False
        else:
            log_summary = f"No local copy of `{dataset_id}` dataset found!"
            return True, True, log_summary, log_summary, True, False
    else:
        log_summary = f"This is not the page you are looking for!"
        return True, True, log_summary, log_summary, True, False


@callback(Output('local-file-browser', 'files'),
          Output('file-browser-modal', 'is_open'),
          Input('explore-button', 'n_clicks'),
          State('dataset-id', 'data'),
          prevent_initial_call=True)
def generate_local_directory_subtree(n_click, dataset_id):
    from plant3dvision.webui.utils import generate_file_list
    dataset_path = temp_scan_dir(dataset_id)
    if dataset_path.is_dir():
        return generate_file_list(dataset_path), True
    else:
        return [], True


# Callback of the 'start-reconstruct-button' button:
@callback(Output('start-reconstruct-button', "disabled", allow_duplicate=True),
          Output('upload-button', "disabled", allow_duplicate=True),
          Output("clean-button", "disabled", allow_duplicate=True),
          Output("remove-button", "disabled", allow_duplicate=True),
          Output('reconstruct-response', 'children'),
          Output('reconstruct-output', 'children'),
          Input('start-reconstruct-button', 'n_clicks'),
          State('task-dropdown', 'value'),
          State('dataset-id', 'data'),
          State('reconstruct-cfg-toml', 'value'),
          State('new-reconstruct', 'data'),
          State('rest-api-host', 'data'),
          State('rest-api-port', 'data'),
          background=True,
          running=[
              (Output('start-reconstruct-button', "disabled"), True, False),
              (Output('start-reconstruct-button', "children"),
               [dbc.Spinner(size="sm"), " Running reconstruction..."],
               [html.I(className="bi bi-check me-2"), "Reconstructed"]),
              (Output("cancel-reconstruct-button", "disabled"), False, True),
              (Output('explore-button', "disabled"), False, False),
          ],
          cancel=[Input("cancel-reconstruct-button", "n_clicks")],
          prevent_initial_call=True)
def reconstruct(n_clicks, task, dataset_id, cfg, new_reconstruct, host, port):
    """Call the `romi_run_task` to execute selected task on dataset using defined configuration."""
    print(f"Clicked {n_clicks} times to run task `{task}` on {dataset_id}!")
    # Import the dataset to process:
    dataset_path = import_dataset_archive(dataset_id, host, port)
    # Clean it, if requested:
    if new_reconstruct:
        clean_temp_scan_dir(n_clicks, dataset_id)
    # Run the reconstruction pipeline:
    success, log_fname = run_reconstruct(dataset_id, task, cfg)
    # Read the log and format it to use in a markdown container:
    log = "```\n" + f"{read_log(dataset_path / log_fname)}```"
    if success:
        return True, False, False, False, f"Task `{task}` performed **successfully** on dataset _{dataset_id}_ !", log
    else:
        return False, False, False, False, f"Task `{task}` **failed**, have look at the log!", log
