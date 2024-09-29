"""List habits.

Usage: 
    habit-list [options]

Options:
    -h, --help       Show this message.
    --version        Show version information.
"""

import requests
from requests.auth import HTTPBasicAuth

import json

from docopt import docopt

from .config.tasks import TasksConfigFile


def format_habit_list(habits):
    return ", ".join(map(lambda h: '#' + h['tagname'], habits))


def print_habit_list(config):
    url = f"{config.url}/habit-api/"

    r = requests.get(url, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        print(format_habit_list(r.json()['results']))
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))


def main():
    arguments = docopt(__doc__, version='1.0.0')

    config = TasksConfigFile()

    print_habit_list(config)

