"""Connect to the Tasks Collector.

Usage: 
    tasks [options]

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

from collections.abc import Iterable

import subprocess
from difflib import SequenceMatcher

import shlex
import sys

try:
    import readline
except ImportError:
    pass


def get_input_until(predicate, prompt=None):
    text = None
    
    while text is None or not predicate(text):
        text = input(prompt)
    
    return text


HELP = """
Available commands:
{commands}

Quit by pressing Ctrl+D or Ctrl+C.
"""


def list_to_points(list):
    return "\n".join([f"  {item}" for item in list])


def help():
    return HELP.format(
        commands=list_to_points(commands.keys())
    )


def print_help(*args):
    print(help())

commands = {
    'observation': 'observation',
    'olist': ['observation', '-l'],
    'quest': 'quest',
    'journal': 'journal',
    'update': 'update',
    'help': print_help,
}


def match_text_against_commands(text):
    for command in commands.keys():
        if command.startswith(text):
            return commands[command]
    
    return None


def run_command(command, args, config, default_thread):
    if callable(command):
        command(args, config, default_thread)
        return

    if type(command) == str:
        command = [command]

    if isinstance(command, Iterable):
        try:
            command_list = command + args
            return_code = subprocess.call(command_list)
            if return_code != 0:
                print(f"Command exited with return code {return_code}", file=sys.stderr)
            
            return
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)

            return
    
    raise TypeError(f"Invalid command: {command}")


def run_single_task(config, default_thread):
    original_text = get_input_until(bool, prompt="> ")

    parts = shlex.split(original_text)

    command = match_text_against_commands(parts[0])

    if command is not None:
        run_command(command, parts[1:], config, default_thread)
        
        return

    add_task(config, default_thread, original_text)


def add_task(config, default_thread, text):
    payload = {
        'thread-name': default_thread,
        'text': text,
    }

    url = '{}/boards/append/'.format(config.url)

    r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        print(GOTOURL.format(url=config.url, name=default_thread).strip())
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))


def main():
    arguments = docopt(__doc__ + help(), version='1.0')

    config = TasksConfigFile()

    print("Connected to Tasks Collector at {}".format(config.url))

    try:
        consume(repeatfunc(
            run_single_task,
            None,
            config,
            arguments['--thread'],
        ))
    except (KeyboardInterrupt, EOFError):
        print("Exiting...")