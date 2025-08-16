"""Connect to the Tasks Collector.

Usage: 
    tasks [options]

Options:
    --thread THREAD  Use specific thread [default: Inbox].
    -h, --help       Show this message.
    --version        Show version information.

By default, tasks are added to the "Inbox" thread.
By prefixing a line with `!` or `#`, it will be added to the Habit Tracker instead.
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
    import os
    import atexit
    readline_available = True
except ImportError:
    readline_available = False

from .quick_notes import get_quick_notes_as_string
from .habits import add_habit
from .plans import get_plan_for_today

import re

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

DEFAULT_THREAD = 'Inbox'


def setup_readline_history(config):
    """Set up readline history functionality."""
    if not readline_available:
        return
    
    # Set history file path
    history_file = os.path.expanduser('~/.tasks_history')
    
    # Load existing history
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass  # No history file exists yet
    except PermissionError:
        pass  # Can't read history file
    
    # Set maximum history size
    readline.set_history_length(1000)
    
    # Save history on exit
    def save_history():
        try:
            readline.write_history_file(history_file)
        except PermissionError:
            pass  # Can't write history file
    
    atexit.register(save_history)


def list_to_points(list):
    return "\n".join([f"  {item}" for item in list])


def help():
    return HELP.format(
        commands=list_to_points(commands.keys())
    )


def print_help(*args):
    print(help())


def open_observation(args, config, default_thread):
    subprocess.call(['open', f"{config.url}/observations/{args[0]}"])


commands = {
    'observation': 'observation',
    'olist': ['observation', '-l'],
    'habits': 'habits',
    'hlist': ['habits', '-l'],
    'oedit': open_observation,
    'edit': open_observation,
    'quest': 'quest',
    'journal': 'journal',
    'thought': ['journal', '-T', 'thoughts'],
    'update': 'update',
    'help': print_help,
    'clear': 'clear',
    'wtf': ['journal', '-T', 'wtf'],
    'nove': ['journal', '-T', 'nove'],
    'reflect': 'reflect',
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


def is_habit_command(text):
    return text.startswith('!') or text.startswith('#')


def run_single_task(config, default_thread):
    if default_thread != DEFAULT_THREAD:
        original_text = get_input_until(bool, prompt=f"({default_thread}) > ")
    else:
        original_text = get_input_until(bool, prompt="> ")

    parts = shlex.split(original_text)

    if is_habit_command(parts[0]):
        add_habit(config, original_text)
        return

    command = match_text_against_commands(parts[0])

    if command is not None:
        run_command(command, parts[1:], config, default_thread)
        
        return

    add_task(config, default_thread, original_text)


RE_THREAD = re.compile(r'^(.*?)\s*>\s*([A-Za-z0-9_-]+)\s*$')

def add_task(config, default_thread, text):
    match = RE_THREAD.match(text)

    if match:
        text = match.group(1).strip()
        thread = match.group(2).strip()
    else:
        thread = default_thread

    payload = {
        'thread-name': thread,
        'text': text,
    }

    url = '{}/boards/append/'.format(config.url)

    r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        print(GOTOURL.format(url=config.url, name=thread).strip())
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))


def main():
    arguments = docopt(__doc__ + help(), version='1.0.2')

    config = TasksConfigFile()
    
    # Set up readline history
    setup_readline_history(config)

    print("Connected to Tasks Collector at {}".format(config.url))

    quick_notes = get_quick_notes_as_string(config).strip()

    print(quick_notes)

    plan = get_plan_for_today(config)

    print(plan)

    try:
        consume(repeatfunc(
            run_single_task,
            None,
            config,
            arguments['--thread'],
        ))
    except (KeyboardInterrupt, EOFError):
        print("Exiting...")
