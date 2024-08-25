"""Add a task.

Usage: 
    addtask [options] [TEXT]

Options:
    --thread THREAD  Use specific thread [default: Inbox].
    -h, --help       Show this message.
    --version        Show version information.
"""

GOTOURL = """
See more:
- {url}/todo/#/board/{name}
"""

import json

from docopt import docopt

import requests
from requests.auth import HTTPBasicAuth

from more_itertools import repeatfunc, consume

from .config.tasks import TasksConfigFile


def get_input_until(predicate, prompt=None):
    text = None
    
    while text is None or not predicate(text):
        text = input(prompt)
    
    return text


def run_single_task(config, thread, text):
    payload = {
        'thread-name': thread,
        'text': text or get_input_until(bool, prompt="> "),
    }

    url = '{}/boards/append/'.format(config.url)

    r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        print("Task added.")
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))


def main():
    arguments = docopt(__doc__, version='1.0.3')

    config = TasksConfigFile()

    text = arguments['TEXT'] or None
    times = 1 if arguments['TEXT'] else None

    try:
        consume(repeatfunc(
            run_single_task,
            times,
            config,
            arguments['--thread'],
            text,
        ))
    except KeyboardInterrupt:
        print("Exiting...")

    print(GOTOURL.format(url=config.url, name=arguments['--thread']).strip())
