#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import numpy as np
from plant3dvision.utils import is_radians
from plant3dvision.utils import locate_task_filesets
from plantdb import FSDB
from plantdb.io import read_graph
from plantdb.io import read_json
from plantdb.io import read_point_cloud
from plantdb.io import read_triangle_mesh


def get_3d_data(db_path, dataset_name):
    """Load the computed data from tasks PointCloud, TriangleMesh, TreeGraph & AnglesAndInternodes.

    Parameters
    ----------
    db_path : str or pathlib.Path
        The path to the dataset containing the data to load.
        Should be in a local ROMI database (FSDB).
    dataset_name : str
        Name of the dataset to load from the database.

    Returns
    -------
    dict
        A dictionary containing the loaded 3D data to render.
    """
    global logger  # use the global logger

    # Connect to the local ROMI database:
    db = FSDB(db_path)
    db.connect()
    # Get the `Scan` instance, should exist:
    scan = db.get_scan(dataset_name, create=False)
    # Find the filesets corresponding to the tasks:
    fileset_names = locate_task_filesets(scan, TASKS)

    # - Try to load the result of the `PointCloud` task:
    fs = scan.get_fileset(fileset_names['PointCloud'])
    try:
        pcd_file = fs.get_file('PointCloud')
        pcd = read_point_cloud(pcd_file)
    except:
        logger.error(f"Could not find a 3D point cloud to load!")
        sys.exit("It seems that no reconstruction pipeline have been run on this dataset!")
    else:
        logger.info(f"Found a 3D point cloud to load: '{pcd_file.filename}'.")

    # - Try to load the result of the `TriangleMesh` task:
    mesh = None
    fs = scan.get_fileset(fileset_names['TriangleMesh'])
    try:
        mesh_file = fs.get_file('TriangleMesh')
        mesh = read_triangle_mesh(mesh_file)
    except:
        logger.warning(f"Could not find a 3D triangular mesh to load!")
    else:
        logger.info(f"Found a 3D triangular mesh to load: '{mesh_file.filename}'.")

    # - Try to load the result of the `TreeGraph` task:
    tree = None
    fs = scan.get_fileset(fileset_names['TreeGraph'])
    try:
        tree_file = fs.get_file('TreeGraph')
        tree = read_graph(tree_file)
    except:
        logger.warning(f"Could not find a 3D tree graph to load!")
    else:
        logger.info(f"Found a 3D tree graph to load: '{tree_file.filename}'.")

    # - Try to load the estimated fruit directions from the `AnglesAndInternodes` task:
    fruit_dir = None
    fs = scan.get_fileset(fileset_names['AnglesAndInternodes'])
    try:
        fruit_dir_file = fs.get_file('fruit_direction')
        fruit_dir = read_json(fruit_dir_file)
    except:
        logger.warning(f"Could not find a list of fruit directions to load!.")
    else:
        logger.info(f"Found a list of fruit directions to load: '{fruit_dir_file.filename}'.")

    # - Try to load the estimated stem directions from the `AnglesAndInternodes` task:
    stem_dir = None
    fs = scan.get_fileset(fileset_names['AnglesAndInternodes'])
    try:
        stem_dir_file = fs.get_file('stem_direction')
        stem_dir = read_json(stem_dir_file)
    except:
        logger.warning(f"Could not find a list of stem directions to load!.")
    else:
        logger.info(f"Found a list of stem directions to load: '{stem_dir_file.filename}'.")

    db.disconnect()  # disconnect from the database
    return {"PointCloud": pcd, "TriangleMesh": mesh, "TreeGraph": tree,
            "FruitDirection": fruit_dir, "StemDirection": stem_dir}


def get_sequences_data(db_path, dataset_name):
    """Get the angle and internode sequences from the `AnglesAndInternodes` task.

    Parameters
    ----------
    db_path : str or pathlib.Path
        The path to the local ROMI database (FSDB).
    dataset_name : str
        Name of the dataset to load from the database.

    Returns
    -------
    dict
        A dictionary containing the loaded angle and internode sequences.
    """
    global logger

    # Connect to the local ROMI database:
    db = FSDB(db_path)
    db.connect()
    # Get the `Scan` instance, should exist:
    scan = db.get_scan(dataset_name, create=False)
    # Find the fileset corresponding to the task:
    fileset_names = locate_task_filesets(scan, TASKS)
    # Load the measures fileset:
    measures_fs = scan.get_fileset(fileset_names['AnglesAndInternodes'])
    measures_file = measures_fs.get_file('AnglesAndInternodes')
    measures = read_json(measures_file)
    try:
        assert measures != {}
    except:
        measures = {"angles": [np.nan], "internodes": [np.nan]}
        logger.warning(f"No AnglesAndInternodes sequences found!")
    else:
        angles = measures["angles"]
        internodes = measures["internodes"]
        logger.info(f"Found a sequence of {len(angles)} angles.")
        logger.info(f"Found a sequence of {len(internodes)} internodes.")
        # Convert angles if in radians
        if is_radians(measures["angles"]):
            from math import degrees
            measures["angles"] = list(map(degrees, measures["angles"]))
            logger.info("Converted estimated angles from radians to degrees.")

    db.disconnect()  # disconnect from the database
    return {'angles': measures["angles"], 'internodes': measures["internodes"]}
