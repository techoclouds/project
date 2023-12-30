#!/bin/sh


# run a worker :)
celery -A backend worker --loglevel=info --concurrency 1 -E
