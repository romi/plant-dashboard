#!/usr/bin/env python3
# -*- coding: utf-8 -*-

broker_url = "redis://172.17.0.2:6379/0"
result_backend = "redis://172.17.0.2:6379/1"

worker_log_color = True
#worker_log_format = "%(log_color)s%(levelname)-8s%(reset)s %(bg_blue)s[%(name)s]%(reset)s %(message)s"

# Enables extended task result attributes (name, args, kwargs, worker, retries, queue, delivery_info) to be written to backend.
result_extended = True
