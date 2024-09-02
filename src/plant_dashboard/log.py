#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from romitask.log import DATE_FMT
from romitask.log import DEFAULT_LOG_LEVEL
from romitask.log import SIMPLE_FMT

LOG_CFG = {
    'version': 1,
    'formatters': {
        'simpleFormatter': {
            'format': SIMPLE_FMT,
            'datefmt': DATE_FMT,
        }
    },
    'handlers': {
        'fileHandler': {
            'class': 'logging.FileHandler',
            'level': {DEFAULT_LOG_LEVEL},
            'formatter': 'simpleFormatter',
            'mode': 'w',
            'filename': '/tmp/webui_reconstruct.log',
        }
    },
    'loggers': {
        'root': {'level': {DEFAULT_LOG_LEVEL}, 'handlers': ['fileHandler']},
    }
}


def get_file_logger(name, path, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create a file handler
    fname = f'{path}{name}.log'
    file_handler = logging.FileHandler(fname, mode='w')
    file_handler.setLevel(level)

    # Create a formatter and add it to the handler:
    formatter = logging.Formatter(SIMPLE_FMT)
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler)
    return logger, fname


def md_formatter(line):
    """Markdown formatter for single line of file logger output, based on `SIMPLE_FMT`."""
    try:
        time, level, name, msg = line.split(" - ")
    except ValueError:
        return line
    else:
        return f"`{time}` - **{level}** - {name} - {msg}"
