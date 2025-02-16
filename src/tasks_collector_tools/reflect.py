"""Reflect on a day, week or month.

Usage: 
    reflect [options]

Options:
    -d, --date DATE  Use this date for reflection.
    -w, --week       Use this week for reflection.
    -m, --month      Use this month for reflection.
    -y, --yesterday  Use yesterday for reflection.
    -h, --help       Show this message.
    --version        Show version information.
"""

TEMPLATE = """
> Thread: {thread}
> Published: {published}
> Tags: {tags}
{notes}
{plan}
# Comment

{comment}

"""

GOTOURL = """
See more:
- {url}/
"""

import json, os, re, sys

from docopt import docopt

from datetime import datetime, date, timedelta

import tempfile

import subprocess

import requests
from requests.exceptions import ConnectionError

from requests.auth import HTTPBasicAuth

from pathlib import Path

from .config.tasks import TasksConfigFile

from .quick_notes import get_quick_notes_as_string

from .plans import get_plan_for_today
from .utils import sanitize_fields, get_cursor_position, sanitize_list_of_strings

from dateutil.parser import parse

import calendar

from pprint import pprint

def get_start_and_end_of_week(date):
    return date.replace(day=date.day - date.weekday()), date.replace(day=date.day - date.weekday() + 6)

def get_start_and_end_of_month(date):
    return date.replace(day=1), date.replace(day=calendar.monthrange(date.year, date.month)[1])

def get_fetch_thread_from_arguments(arguments):
    if arguments['--month']:
        return 'Weekly'
    else:
        return None


def get_save_thread_from_arguments(arguments):
    if arguments['--month']:
        return 'big-picture'
    elif arguments['--week']:
        return 'Weekly'
    else:
        return None


def template_from_arguments(arguments):
    cmd = ['reflectiondump']

    day = parse(arguments['--date']) if arguments['--date'] else date.today()

    thread = get_fetch_thread_from_arguments(arguments)

    if thread is not None:
        cmd += ['--thread', thread]

    if arguments['--week']:
        start, end = get_start_and_end_of_week(day)

    elif arguments['--month']:
        start, end = get_start_and_end_of_month(day)

        cmd += [
            '--skip-journals',
        ]
    elif arguments['--yesterday']:
        start = end = day - timedelta(days=1)
    else:
        start = end = day

    cmd += [
        '-d', start.strftime('%Y-%m-%d'),
        '-D', end.strftime('%Y-%m-%d'),
    ]

    return subprocess.check_output(cmd).decode('utf-8').strip().replace('\r', '')


def template_from_payload(payload):
    payload = payload.copy()

    payload['tags'] = ', '.join(payload['tags'])

    return TEMPLATE.format(notes='', plan='', **payload).lstrip()

title_re = re.compile(r'^##? (Reflection|Better|Best)')


empty_point_re = re.compile(r'^\s*\-\s*(?:\[\s+\])\s*')
point_re = re.compile(r'^\s*\-\s*(?:\[x\^\~\])?\s*')

def add_stack_to_payload(payload, name, lines):
    if name is None:
        return

    if name == 'Reflection':
        name = 'good'

    payload[name.lower()] = ''.join(lines).strip()


DEAD_LETTER_DIRECTORY = os.path.expanduser(os.path.join('~', '.tasks', 'queue'))


def queue_dead_letter(payload, path, metadata):
    if not os.path.exists(path):
        os.makedirs(path)

    basename = "{}".format(datetime.now().strftime("%Y-%m-%d_%H%M%S_journal"))
    name = f'{basename}.json'
    i = 0

    while os.path.exists(name):
        i += 1
        name = f'{basename}-{i}.json'

    with open(os.path.join(path, name), "w") as f:
        json.dump({
            'payload': payload,
            'meta': metadata
        }, f)
    
    return name

def send_dead_letter(path, _metadata):
    metadata = _metadata.copy()

    print(f"Attempting to send {path}...")

    with open(path) as f:        
        data = json.load(f)


        metadata.update(data['meta'])
        payload = data['payload']

        requests.post(metadata['url'], json=payload, auth=metadata['auth'])

    os.unlink(path)


def send_dead_letters(path, metadata):
    for root, dirs, files in os.walk(path):
        for name in sorted(files):
            send_dead_letter(os.path.join(root, name), metadata)


multi_line_re = re.compile(r'\n(\s*\n)+')


JOURNAL_TEMPLATE = """
{good}

{better}

{best} 
"""

def journal_payload_from_reflection_payload(payload, published, thread):
    comment = JOURNAL_TEMPLATE.format(**payload).strip()
    comment = multi_line_re.sub('\n\n', comment)

    return {
        'published': published.isoformat(),
        'comment': comment,
        'thread': thread,
        'tags': [],
        'reflection': True,
    }

def main():
    arguments = docopt(__doc__, version='1.1')

    config = TasksConfigFile()

    tmpfile = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')

    template = template_from_arguments(arguments)

    cursor_position = get_cursor_position(template, "# Reflection")

    with tmpfile:
        tmpfile.write(template)
    
    editor = os.environ.get('EDITOR', 'vim')

    result = subprocess.run([
        editor, f'+{cursor_position}', tmpfile.name,
    ])

    if result.returncode != 0:
        sys.exit(1)

    payload = {
        'good': None,
        'better': None,
        'best': None,
    }

    with open(tmpfile.name) as f:
        current_name = None
        current_stack = []

        for line in f:
            if m := title_re.match(line):
                if current_name is not None:
                    add_stack_to_payload(payload, current_name, current_stack)
                
                current_name = m.group(1).strip()
                current_stack = []
            elif line.strip().startswith('#') and current_name is not None:
                add_stack_to_payload(payload, current_name, current_stack)
                current_name = None
                current_stack = []
            elif not empty_point_re.match(line):
                current_stack.append(line)
    
        if current_name is not None:
            add_stack_to_payload(payload, current_name, current_stack)

    if not payload['good']:
        print("No changes were made to the Comment field.")

        os.unlink(tmpfile.name)

        sys.exit(0)

    published = datetime.now() - timedelta(days=1) if arguments['--yesterday'] else datetime.now()
    thread = get_save_thread_from_arguments(arguments)

    payload = journal_payload_from_reflection_payload(payload, published, thread)

    try:
        send_dead_letters(DEAD_LETTER_DIRECTORY, metadata={
            'auth': HTTPBasicAuth(config.user, config.password)
        })
    except Exception as e:
        print(e)
        print("Error: Failed to send queue")

    url = '{}/journal/'.format(config.url)

    try:
        r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))
    except ConnectionError:
        name = queue_dead_letter(payload, path=DEAD_LETTER_DIRECTORY, metadata={
            'url': url,            
        })

        print("Error: Connection failed.")
        print(f"Your update was saved at {name}.")
        print("It will be sent next time you run this program.")

        sys.exit(2)

    if r.ok:
        new_payload = r.json()

        print(template_from_payload(new_payload))

        print(GOTOURL.format(url=config.url).strip())

        os.unlink(tmpfile.name)
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print("HTTP {}\n{}".format(r.status_code, r.text))
        
        print("The temporary file was saved at {}".format(
            tmpfile.name
        ))



        
            

            
