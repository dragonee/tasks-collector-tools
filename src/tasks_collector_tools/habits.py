"""Track habits daily or list them.

Usage: 
    habits [options]

Options:
    -a, --all        Track all habits.
    --yesterday      Set the date to yesterday.
    -l, --list       List habits
    -o, --output FILENAME  If listing, output to file [default: -]
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

from dataclasses import dataclass

from datetime import datetime, timedelta


def add_habit(config, text, published=None):
    if published is None:
        published = datetime.now()

    payload = {
        'text': text,
        'published': published.astimezone().isoformat()
    }

    url = '{}/habit/track/'.format(config.url)

    r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        print("Habit tracked")
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))


def format_habit_list(habits):
    return ", ".join(map(lambda h: '#' + h['tagname'], habits))


def get_habit_list(config, stderr, date=None):
    url = f"{config.url}/habit-api/"

    if date is not None:
        url += f"?date={date.isoformat()}"

    r = requests.get(url, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        return r.json()['results']
    else:
        try:
            stderr.write(json.dumps(r.json(), indent=4, sort_keys=True) + '\n')
        except json.decoder.JSONDecodeError:
            stderr.write("HTTP {}\n{}".format(r.status_code, r.text) + '\n')


def print_habit_list(config, filename='-'):
    with smart_open(filename, 'w', pipe=sys.stdout) as f:
        habits = get_habit_list(config, sys.stderr)

        f.write(format_habit_list(habits) + '\n')


@dataclass
class Habit:
    id: int
    tagname: str
    name: str
    slug: str
    today_tracked: int
    description: str = None


def ask_for(words, no_words=None, skip_words=None, prompt="{words}"):
    if no_words:
        _prompt = "[{}/{}/{}] ".format(words[0], no_words[0], skip_words[0].upper())
    else:
        _prompt = "[{}/{}] ".format(words[0], skip_words[0].upper())
    
    prompt = prompt.format(words=_prompt)

    def match_any(words, s):
        for word in words:
            if s.startswith(word):
                return (True, s[len(word):].lstrip())
            
        return (False, None)

    while True:
        original_input = input(prompt)

        skip, _ = match_any(skip_words, original_input)

        if original_input == '' or skip:
            return (None, None)
        
        true, s = match_any(words, original_input)

        if true:
            return (True, s)
        
        false, s = match_any(no_words, original_input)
        
        if false:
            return (False, s)


def format_line(habit, answer, text):
    occured = '#' if answer else '!'
    
    return f'{occured}{habit.tagname} {text}'


def get_yesterday_date():
    return (datetime.now() - timedelta(days=1)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )


def main():
    arguments = docopt(__doc__, version='1.1')

    config = TasksConfigFile()

    published = datetime.now()
    if arguments['--yesterday']:
        published = get_yesterday_date()

    if arguments['--list']:
        print_habit_list(config, arguments['--output'])
        return
    
    raw_habits = get_habit_list(config, sys.stderr, date=published.date())

    habits = map(lambda h: Habit(**h), raw_habits)

    if arguments['--all']:
        habits_without_ignored = habits
    else:
        habits_without_ignored = filter(lambda h: h.tagname not in config.ignore_habits, habits)

    non_tracked_habits = filter(lambda h: h.today_tracked == 0, habits_without_ignored)

    try:
        for habit in non_tracked_habits:
            answer, text = ask_for(['y', 't'], ['n', 'f'], ['s'], prompt=f'#{habit.tagname} {{words}}')

            if answer is None:
                continue
            
            add_habit(config, format_line(habit, answer, text), published=published)
    except (KeyboardInterrupt, EOFError):
        print()
        return
