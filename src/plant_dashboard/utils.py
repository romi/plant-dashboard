#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import tempfile
from io import BytesIO
from logging import getLogger
from pathlib import Path
from zipfile import ZipFile

import requests
import toml
from dash import dcc
from dash import html

from plantdb.fsdb import MARKER_FILE_NAME
from plantdb.rest_api_client import base_url
from plantdb.rest_api_client import list_scan_names
from plantdb.rest_api_client import parse_scans_info
from romitask.cli.romi_run_task import run_task
from romitask.log import get_log_filename

FONT_FAMILY = '"Nunito Sans", sans-serif'

TASKS = [
    "PointCloud",
    "TriangleMesh",
    "CurveSkeleton",
    "TreeGraph",
    "AnglesAndInternodes",
]

TASK_OBJECTS = [
    "PointCloud",
    "TriangleMesh",
    "TreeGraph",
    "FruitDirection",
    "StemDirection",
]

IMAGE_TASKS = [
    'images',
    'Undistorted',
    'Masks',
]


def t_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_dataset_dict(host, port):
    """Returns the dataset dictionary for the PlantDB REST API at given host url and port.

    Parameters
    ----------
    host : str
        The hostname or IP address of the PlantDB REST API server.
    port : str
        The port number of the PlantDB REST API server.

    Returns
    -------
    dict
        The dataset dictionary for the PlantDB REST API at given host url and port.

    See Also
    --------
    plantdb.rest_api_client.list_scan_names
    plantdb.rest_api_client.parse_scans_info
    """
    scans_list = list_scan_names(host, port)
    if len(scans_list) > 0:
        dataset_dict = parse_scans_info(host, port)
    else:
        dataset_dict = None
    return dataset_dict


def pipeline_cfg_url(host, port, scan_id):
    """Get the URL corresponding to the 'pipeline.toml' backup file for the given scan ID in a PlantDB REST API.

    Parameters
    ----------
    host : str
        The hostname or IP address of the PlantDB REST API server.
    port : str
        The port number of the PlantDB REST API server.
    scan_id : str
        The name of the dataset to test for the reconstruction pipeline.

    Returns
    -------
    str
        The URL corresponding to the 'pipeline.toml' backup file for the given scan ID.
    """
    return f"{base_url(host, port)}/files/{scan_id}/pipeline.toml"


def get_pipeline_cfg(host, port, scan_id):
    """Get the backup configuration file of the reconstruction pipeline for the given scan ID.

    Parameters
    ----------
    host : str
        The hostname or IP address of the PlantDB REST API server.
    port : str
        The port number of the PlantDB REST API server.
    scan_id : str
        The name of the dataset to test for the reconstruction pipeline.

    Returns
    -------
    dict
        The backup configuration for the reconstruction pipeline for the given scan ID.

    Examples
    --------
    >>> from plant3dvision.webui.utils import get_pipeline_cfg
    >>> get_pipeline_cfg('127.0.0.1','5000','real_plant')
    {}
    >>> cfg = get_pipeline_cfg('127.0.0.1','5000','real_plant_analyzed')
    """
    if has_pipeline_cfg(host, port, scan_id):
        return toml.loads(requests.get(pipeline_cfg_url(host, port, scan_id)).content.decode())
    else:
        return {}


def has_pipeline_cfg(host, port, scan_id):
    """Test if a named dataset has a reconstruction pipeline.

    Reconstruction pipeline are named 'pipeline.toml', so we test if the request from the file ressource is ok.

    Parameters
    ----------
    host : str
        The hostname or IP address of the PlantDB REST API server.
    port : str
        The port number of the PlantDB REST API server.
    scan_id : str
        The name of the dataset to test for the reconstruction pipeline.

    Returns
    -------
    bool
        Indicates if a reconstruction pipeline is found.

    Examples
    --------
    >>> from plant3dvision.webui.utils import has_pipeline_cfg
    >>> has_pipeline_cfg('127.0.0.1','5000','real_plant')
    False
    >>> has_pipeline_cfg('127.0.0.1','5000','real_plant_analyzed')
    True
    """
    return requests.get(pipeline_cfg_url(host, port, scan_id)).ok


def temp_fsdb_dir(scan_id):
    """Path to the temporary FSDB directory."""
    return Path(tempfile.gettempdir()) / f'romidb_{scan_id}'


def temp_scan_dir(scan_id):
    """Path to the temporary FSDB dataset directory."""
    return temp_fsdb_dir(scan_id) / scan_id


def create_temp_fsdb(scan_id):
    """Creates a temporary FSDB dataset directory.

    Parameters
    ----------
    scan_id : str
        The name of the dataset to create.

    Returns
    -------
    pathlib.Path
        The path to the temporary FSDB directory.
    pathlib.Path
        The path to the temporary dataset directory.
    """
    # Create a temporary fsdb with the name of the dataset as suffix:
    tmp_db = temp_fsdb_dir(scan_id)
    tmp_db.mkdir(parents=True, exist_ok=True)
    marker_file = tmp_db / MARKER_FILE_NAME  # define the marker file
    marker_file.open(mode='w').close()  # create the marker file
    # Define the local dataset path:
    dataset_path = temp_scan_dir(scan_id)
    dataset_path.mkdir(parents=True, exist_ok=True)
    return tmp_db, dataset_path


def config_upload():
    """The TOML configuration file upload component."""
    return dcc.Upload(id="cfg-upload",
                      children=['Drag and Drop or ', html.B('Select'), ' a TOML configuration file.'],
                      style={
                          'width': '100%',
                          'height': '60px',
                          'lineHeight': '60px',
                          'borderWidth': '1px',
                          'borderStyle': 'dashed',
                          'borderRadius': '5px',
                          'textAlign': 'center',
                      },
                      accept=".toml",
                      # Do not allow multiple files to be uploaded
                      multiple=False
                      )


def _carousel_href(ds_id: str) -> str:
    """The URL pointing to the image carousel for the given dataset."""
    return f"/carousel/{ds_id}"


def _reconstruct_href(ds_id: str) -> str:
    """The URL pointing to the image carousel for the given dataset."""
    return f"/reconstruct/{ds_id}"


def _viewer_href(ds_id: str) -> str:
    """The URL pointing to the data viewer for the given dataset."""
    return f"/3d_viewer/{ds_id}"


def upload_dataset_archive(dataset_id, host, port):
    """Create an archive of the local dataset and send it to the PlantDB REST API using a POST request."""
    # Local path to search for files to archive
    dataset_path = temp_scan_dir(dataset_id)
    # List to store file paths to archive
    file_paths = []
    # Recursively search for files
    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    # Create a zip file in memory
    zip_data = BytesIO()
    with ZipFile(zip_data, mode='w') as zip_file:
        for file_path in file_paths:
            # Check if the file exists
            if os.path.isfile(file_path):
                # Add the file to the zip,
                # removing the path to the scan directory not to get the full path in archived file names
                zip_file.write(file_path,
                               arcname=file_path.replace(str(dataset_path) + '/', ''))
            else:
                print(f"Warning: {file_path} is not a file and will be skipped.")

    # Send the POST request
    url = f"{base_url(host, port)}/archive/{dataset_id}"
    files = {'zip_file': ('archive.zip', zip_data.getvalue())}
    response = requests.post(url, files=files)

    # Check the response to the POST request:
    if response.ok:
        return 'Zip file uploaded successfully', "```\n" + "\n".join(response.json()['files']) + "```"
    else:
        return 'Error uploading zip file', "```\n" + response.text + "```"

def get_all_files(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, directory)
            file_list.append(rel_path)
    return file_list


def upload_dataset(dataset_id, host, port, CHUNK_SIZE=8192):
    from flask import jsonify
    target_url = f"{base_url(host, port)}/files/{dataset_id}"
    # Local path to search for files to send:
    dataset_path = temp_scan_dir(dataset_id)
    # List the files to send:
    files_to_send = get_all_files(dataset_path)

    total_files = len(files_to_send)
    for index, rel_filename in enumerate(files_to_send, start=1):
        file_path = os.path.join(dataset_path, rel_filename)
        file_size = os.path.getsize(file_path)
        # sent_bytes = 0
        #
        # def file_stream(file_path, sent_bytes, CHUNK_SIZE=8192):
        #     with open(file_path, 'rb') as file:
        #         while True:
        #             chunk = file.read(CHUNK_SIZE)
        #             if not chunk:
        #                 break
        #             sent_bytes += len(chunk)
        #             yield chunk
        #
        headers = {
            'Content-Disposition': f'attachment; filename="{rel_filename}"',
            'Content-Length': str(file_size),
            'X-File-Path': f"{rel_filename}",  # Send relative path information
        }
        # if file_size >= CHUNK_SIZE:
        #     headers['X-Chunk-Size'] = str(CHUNK_SIZE)  # Add this line
        #     # Send the chunked file:
        #     response = requests.post(target_url,
        #                              data=file_stream(file_path, sent_bytes, CHUNK_SIZE),
        #                              headers=headers, stream=True)
        # else:
        #     with open(file_path, 'rb') as file:
        #         response = requests.post(target_url, data=file, headers=headers)
        with open(file_path, 'rb') as file:
            response = requests.post(target_url, data=file, headers=headers)

        if response.status_code != 201:
            return f"Error sending file `{rel_filename}`: _{response.json()['error']}_."

        # Update progress
        progress = (index / total_files) * 100
        requests.post('http://localhost:8000/update_progress',
                      json={'progress': progress, 'dataset_id': dataset_id})

    return "All files sent successfully!", files_to_send

def refresh_dataset(dataset_id, host, port):
    req = requests.get(f"{base_url(host, port)}/refresh?scan_id={dataset_id}")
    if req.ok:
        return f"Refreshed `{dataset_id}` successfully in database!"
    else:
        return f"Error refreshing dataset `{dataset_id}`: _{req.text}_."

def import_dataset_archive(dataset_id, host, port):
    req = requests.get(f"{base_url(host, port)}/archive/{dataset_id}")
    if req.ok:
        archive_content = req.content
    else:
        return f"ERROR: Could not access archive for {dataset_id}!"
    # Create a temporary fsdb with the name of the dataset as suffix:
    tmp_db, dataset_path = create_temp_fsdb(dataset_id)
    # Extract the archive in temporary FSDB:
    with ZipFile(BytesIO(archive_content), 'r') as zip_ref:
        zip_ref.extractall(tmp_db)

    return dataset_path


def run_reconstruct(dataset_id, task, cfg):
    # Local path to search for files to archive
    dataset_path = temp_scan_dir(dataset_id)
    # Create a combined logger using the configuration:
    logger = getLogger('reconstruct')
    log_fname = get_log_filename(task)
    success = False
    try:
        run_task(dataset_path, task=task, config=toml.loads(cfg),
                 logger=logger, log_fname=log_fname)
        success = True
    except Exception as e:
        logger.error(e)
    return success, log_fname


def compare_lib_version(cfg_dict, libraries_version):
    """Create a pandas DataFrame comparing libraries versions.

    It compares between a previous reconstruction configuration and the currently installed libraries.

    Parameters
    ----------
    cfg_dict : dict
        The reconstruction configuration dictionary.
    libraries_version : dict
        The currently installed libraries version.

    Returns
    -------
    pandas.DataFrame
        A pandas DataFrame comparing libraries versions.
    """
    import pandas as pd
    if libraries_version is None or libraries_version == {}:
        from romitask.utils import get_version
        libraries_version = get_version()
    prev_version = cfg_dict['version']
    keys = list(set(libraries_version.keys()) | set(prev_version.keys()))
    version_dict = {}
    for key in sorted(keys):
        version_dict[key] = [prev_version.get(key, 'Unknown'), libraries_version.get(key, 'Unknown')]
    df = pd.DataFrame.from_dict(version_dict, orient='index', columns=['previous', 'current'])
    return df


def read_log(log_path):
    """Read and return a file content as a string.

    Parameters
    ----------
    log_path : str
        The path to the log file to load & read.

    Returns
    -------
    str
        The content of the log file.
    """
    with open(log_path, 'rb') as f:
        log = "".join([line.decode() for line in f.readlines()])
    return log

def generate_file_list(root_path):
    """Generate a files list suitable for use with `KeyedFileBrowser` class from `dash_cool_components`.

    Parameters
    ----------
    root_path : str
        The root path of the directory to generate the files list from.

    Returns
    -------
    list
        A file list suitable for use with `KeyedFileBrowser`.
    """
    files_list = []
    import time
    current_time = time.time()
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_stat = os.stat(file_path)
            # Calculate the time delta in days
            modified_delta = (current_time - file_stat.st_mtime)/float(24*60*60)
            files_list.append({
                'key': os.path.relpath(file_path, root_path),
                'modified': modified_delta,
                'size': file_stat.st_size,
            })
    return files_list