"""List habits.

Usage: 
    habits [options]

Options:
    -o, --output FILENAME  Output to file [default: -]
    -h, --help       Show this message.
    --version        Show version information.
"""

import sys

import requests
from requests.auth import HTTPBasicAuth

import json

from docopt import docopt

from .config.tasks import TasksConfigFile
from .utils import smart_open

def format_habit_list(habits):
    return ", ".join(map(lambda h: '#' + h['tagname'], habits))


def _print_habit_list(config, stdout, stderr):
    url = f"{config.url}/habit-api/"

    r = requests.get(url, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        stdout.write(format_habit_list(r.json()['results']) + '\n')
    else:
        try:
            stderr.write(json.dumps(r.json(), indent=4, sort_keys=True) + '\n')
        except json.decoder.JSONDecodeError:
            stderr.write("HTTP {}\n{}".format(r.status_code, r.text) + '\n')


def print_habit_list(config, filename='-'):
    with smart_open(filename, 'w', pipe=sys.stdout) as f:
        _print_habit_list(config, f, sys.stderr)


def main():
    arguments = docopt(__doc__, version='1.0.1')

    config = TasksConfigFile()

    print_habit_list(config, arguments['--output'])

