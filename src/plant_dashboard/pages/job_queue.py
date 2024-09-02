#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import requests
from dash import Input
from dash import Output
from dash import callback
from dash import dcc
from dash import html
from dash import register_page
from future.backports.datetime import datetime
from requests.auth import HTTPBasicAuth

USERNAME = os.environ['FLOWER_USER']
PASSWORD = os.environ['FLOWER_PWD']

register_page(__name__, path_template="/job_queue")

layout = html.Div([
    html.H1("Celery Tasks Monitor"),
    html.Div(id='task-info'),
    dcc.Interval(
        id='interval-component',
        interval=5 * 1000,  # in milliseconds
        n_intervals=0
    )
])


def find_words_in_apostrophes(text):
    """Custom parser to get test between apostrophes."""
    import re
    pattern = r"'([^']+)'"
    matches = re.findall(pattern, text)
    return matches


def custom_args_parse(uuid):
    """Custom parser to get ROMI task name and dataset using a task 'args' info by flower API."""
    response = requests.get(f'http://0.0.0.0:5555/api/task/info/{uuid}', auth=HTTPBasicAuth(USERNAME, PASSWORD))
    content = response.content.decode()
    content = eval(content.replace('null', 'None'))
    if not isinstance(content['args'], str):
        return "?", "?"
    try:
        # Finished tasks:
        _, _, task, dataset_id = find_words_in_apostrophes(content['args'])[:4]
    except ValueError:
        # Running/pending tasks
        task, dataset_id, _ = find_words_in_apostrophes(content['args'])[:3]
    return task, dataset_id


def process_datetime(value) -> str:
    """Convert the given time value from EPOCH to human-readable format YYYY-MM-DD HH:MM:SS."""
    if value is not None:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    else:
        return 'None'


def process_flower_tasks(flower_tasks):
    """Create a pandas DataFrame gathering the celery tasks to display in AG Grid.

    Returns
    -------
    pandas.DataFrame
        The DataFrame gathering the celery tasks to display.
    """
    task_table = {col: [] for col in ['uuid', 'state', 'task', 'dataset', 'received', 'started', 'succeeded']}
    for uuid, task in flower_tasks.items():
        task_table['uuid'].append(uuid)
        task_name, dataset_id = custom_args_parse(uuid)
        task_table['state'].append(task['state'])
        task_table['task'].append(task_name)
        task_table['dataset'].append(dataset_id)
        task_table['received'].append(process_datetime(task['received']))
        task_table['started'].append(process_datetime(task['started']))
        task_table['succeeded'].append(process_datetime(task['succeeded']))
    return pd.DataFrame().from_dict(task_table)


def _column_defs(col_name):
    """Set the properties of the AG Grid columns."""
    cdef = {"field": col_name, 'filter': True}
    # 'Badge' is defined in assets/dashAgGridComponentFunctions.js
    cdef['cellRenderer'] = 'Badge' if col_name == 'state' else 'text'
    return cdef


def _alert_msg(msg) -> dbc.Alert:
    return dbc.Alert([html.I(className="bi bi-exclamation-diamond me-2"), msg], color="warning")


def _error_msg(msg) -> dbc.Alert:
    return dbc.Alert([html.I(className="bi bi-bug me-2"), msg], color="danger")


# @callback(Output('task-info', 'children'),
#     Input('interval-component', 'n_intervals'))
@callback(Output('task-info', 'children'),
          Input('url', 'pathname'))
def update_task_info(pathname):
    # Update the table only if on the page:
    if pathname != '/job_queue':
        return []

    try:
        response = requests.get('http://0.0.0.0:5555/api/tasks',
                                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                                timeout=10)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        return _error_msg(f"A ConnectionError occurred: {e}")
    except requests.exceptions.Timeout as e:
        return _error_msg(f"The request timed out: {e}")
    except requests.exceptions.RequestException as e:
        return _error_msg(f"An error occurred while making the request: {e}")

    if response.ok:
        # Process and format task information as needed
        tasks = response.json()
        if len(tasks) == 0:
            task_table = dbc.Alert([html.I(className="bi bi-info-circle me-2"),
                                    "No tasks found! You probably did not reconstruct anything... YET!"],
                                   color="info",
                                   )
        else:
            flower_tasks_df = process_flower_tasks(tasks)
            task_table = dag.AgGrid(
                id="tasks-dag",
                rowData=flower_tasks_df.to_dict("records"),
                columnDefs=[_column_defs(col) for col in flower_tasks_df.columns],
                getRowId="params.data.Name",
                dashGridOptions={"animateRows": False, "pagination": True, "paginationAutoPageSize": True},
                persistence=True,
                persisted_props=["filterModel"],
                columnSize="autoSize",
                style={"height": '80vh', "width": "100%"}, )
    else:
        return _alert_msg(f"Error accessing Flower API: {response.status_code}")

    return task_table
