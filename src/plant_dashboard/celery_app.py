#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from celery import Celery

from plant3dvision.webui.utils import import_dataset_archive
from plant3dvision.webui.utils import refresh_dataset
from plant3dvision.webui.utils import run_reconstruct
from plant3dvision.webui.utils import upload_dataset

# Create a Celery APP to handle background (long-running) callbacks:
celery_app = Celery(__name__,
                    # Start a redis docker, named 'some-redis' with:
                    # $ docker run --name some-redis -d -p 6379:6379 redis
                    # Then get the IP address using its name with:
                    # $ docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' some-redis
                    # broker="redis://172.17.0.2:6379/0",
                    # backend="redis://172.17.0.2:6379/1",
                    # include=[
                    #    "plant3dvision.webui.app",
                    # ]
                    )

celery_app.config_from_object('plant3dvision.webui.celeryconfig')


# print(f"result_extended = {celery_app.conf.result_extended}")


# print(celery_app.conf)

@celery_app.task
def task_import_dataset_archive(host, port, dataset_id):
    return import_dataset_archive(dataset_id, host, port)


# @celery_app.task
# def task_run_reconstruct(dataset_id, task, cfg):
#    return run_reconstruct(dataset_id, task, cfg)


@celery_app.task
def task_run_reconstruct(dataset_id, task, cfg, new_reconstruct, host, port):
    """Call the `romi_run_task` to execute selected task on dataset using defined configuration."""
    from plant3dvision.webui.pages.reconstruct import clean_temp_scan_dir
    print(f"Run task `{task}` on {dataset_id}!")
    # Import the dataset to process:
    _ = import_dataset_archive(dataset_id, host, port)
    # Clean it, if requested:
    if new_reconstruct:
        clean_temp_scan_dir(0, dataset_id)
    # Run the reconstruction pipeline:
    _, _ = run_reconstruct(dataset_id, task, cfg)
    # Upload the processed dataset with pipeline outputs:
    _, _ = upload_dataset(dataset_id, host, port)
    # Call a refresh on this dataset as new filesets & files are now available:
    _ = refresh_dataset(dataset_id, host, port)
    return


@celery_app.task
def task_upload_dataset(host, port, dataset_id):
    return upload_dataset(dataset_id, host, port)
