"""Dump observations to markdown files.

Usage: 
    eventdump [options] [PATH]

Options:
    -d DATE_FROM, --from FROM  Dump from specific date.
    -D DATE_TO, --to DATE_TO   Dump to specific date.
    --year YEAR      Dump specific year.
    -h, --help       Show this message.
    --version        Show version information.
"""

VERSION = '1.0'

import json, os, re, sys, pprint

from docopt import docopt

from datetime import datetime, date, timedelta

import tempfile

import subprocess

import requests
from requests.auth import HTTPBasicAuth

from pathlib import Path

from .config.tasks import TasksConfigFile

from slugify import slugify

from urllib.parse import urlencode

from dateutil.parser import parse

from dataclasses import asdict, field

import re

from textwrap import dedent, fill

from pydantic import BaseModel
from typing import List, Optional, Literal, Union

from collections import Counter
from .utils import render_template

EVENT_TEMPLATE = """
### {{ resourcetype }}: {{ published }}

{{ comment }}
"""


TEMPLATE = """
# {{ date }}
{% if plan.has_focus %}
{{ plan.focus_list }}
{% endif %}

{% if plan.has_want %}
## Want

{{ plan.want_list }}
{% endif %}

{% if habits %}
## Habits

{{ habits }}
{% endif %}
{% if observation_stats.count %}
## Work on observations ({{ observation_stats.count }})

{{ observation_stats.renders }}
{% endif %}
{% if events %}
## Journals

{{ events }}
{% endif %}
{% if reflection %}
## Reflection
{% endif %}

{% if reflection.has_good %}
{{ reflection.good_list }}
{% endif %}

{% if reflection.has_better %}
### Better

{{ reflection.better_list }}
{% endif %}

{% if reflection.has_best %}
### Best

{{ reflection.best_list }}
{% endif %}
"""

def first_line(text):
    splitted = text.split('\n')

    if len(splitted) > 1:
        return splitted[0].rstrip().rstrip('.…') + '…'

    return text


class BaseEvent(BaseModel):
    id: int
    published: datetime
    resourcetype: str

    template: str = None

    def render(self):
        return render_template(self.get_template(), self)
    
    def nice_published(self):
        return self.published.strftime('%H:%M')
    
    base_template: str = """
    ### {{ nice_published }}: {{ resourcetype }}
    """

    def get_template(self):
        return dedent(self.base_template) + '\n' + dedent(self.template)

class Habit(BaseModel):
    id: int
    name: str
    description: Optional[str]
    slug: str
    tagname: str

RE_SOMETIME = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?')

class JournalAdded(BaseEvent):
    resourcetype: Literal['JournalAdded']
    comment: str
    tags: List[str]

    # Added after removed Observation events from parsing
    base_template: str = """
    ### {{ nice_published }}
    """

    template: str = """    
    {{ comment }}
    """

    def nice_published(self):
        published_time = self.published.time()

        if published_time.hour == 23 and published_time.minute == 59 and published_time.second == 59:
            return 'At the end of the day...'

        if published_time.hour == 0 and published_time.minute == 0 and published_time.second == 0:
            match = RE_SOMETIME.search(self.comment)

            if match:
                return match.group(0)

            return 'Sometime that day...'

        return super().nice_published()

class HabitTracked(BaseEvent):
    resourcetype: Literal['HabitTracked']
    note: str
    occured: bool
    habit: Habit

    def render(self):
        if self.nice_published() == '00:00':
            return f'- {self.get_note()}'

        return f'- {self.nice_published()}: {self.get_note()}'

    def get_note(self):
        if not self.note:
            occured_str = '#' if self.occured else '!'

            return f'{occured_str}{self.habit.tagname}'
        
        return self.note

class ObservationEvent(BaseEvent):
    url: str

class ObservationMade(ObservationEvent):
    resourcetype: Literal['ObservationMade']
    event_stream_id: str
    type: str
    situation: str
    interpretation: Optional[str]
    approach: Optional[str]

    template: str = """    
    {{ situation }}
    {% if interpretation %}
    ### Interpretation
    
    {{ interpretation }}
    {% endif %}
    {% if approach %}
    ### Approach

    {{ approach }}
    {% endif %}
    """

class ObservationUpdated(ObservationEvent):
    resourcetype: Literal['ObservationUpdated']
    event_stream_id: str
    observation_id: Optional[int]
    situation_at_creation: str
    comment: str

    base_template: str = """
    ### {{ nice_published }}: {{ resourcetype }} ({{ observation }})
    """

    template: str = """
    {% if situation_at_creation %}
    > {{ situation_line }}
    {% endif %}
    {{ comment }}
    """

    def situation_line(self):
        return first_line(self.situation_at_creation)

    def observation(self):
        if self.observation_id:
            return f'#{self.observation_id}'
        
        return self.event_stream_id

class ObservationRecontextualized(ObservationEvent):
    resourcetype: Literal['ObservationRecontextualized']
    event_stream_id: str
    situation: str
    old_situation: str

    template: str = """    
    {{ situation }}
    """

class ObservationReinterpreted(ObservationEvent):
    resourcetype: Literal['ObservationReinterpreted']
    event_stream_id: str
    interpretation: Optional[str]
    old_interpretation: Optional[str]
    situation_at_creation: str

    template: str = """
    {% if situation_at_creation %}
    > {{ situation_line }}
    {% endif %}
    {{ interpretation }}
    """

    def situation_line(self):
        return first_line(self.situation_at_creation)

class ObservationReflectedUpon(ObservationEvent):
    resourcetype: Literal['ObservationReflectedUpon']
    event_stream_id: str
    approach: Optional[str]
    old_approach: Optional[str]
    situation_at_creation: str

    template: str = """
    {% if situation_at_creation %}
    > {{ situation_line }}
    {% endif %}
    {{ approach }}
    """

    def situation_line(self):
        return first_line(self.situation_at_creation)   

class ObservationClosed(ObservationEvent):
    resourcetype: Literal['ObservationClosed']
    event_stream_id: str
    type: str
    situation: str
    interpretation: Optional[str]
    approach: Optional[str]

    template: str = """
    {{ situation }}

    {% if interpretation %}
    ### Interpretation

    {{ interpretation }}
    {% endif %}
    {% if approach %}
    ### Approach

    {{ approach }}
    {% endif %}
    """

def listize(text):
    return '\n'.join(f'- {line.lstrip("-")}' for line in text.split('\n') if line.strip())

def not_empty(text):
    return text and text.strip() != '' and text.strip() != '?'

class Plan(BaseModel):
    id: int
    focus: str
    want: str
    pub_date: date

    def empty(self):
        return not self.has_want() and not self.has_focus()

    def has_want(self):
        return not_empty(self.want)

    def has_focus(self):
        return not_empty(self.focus)
    
    def want_list(self):
        return listize(self.want)
    
    def focus_list(self):
        return listize(self.focus)

class Reflection(BaseModel):
    id: int
    good: str
    better: str
    best: str
    pub_date: date

    def empty(self):
        return not self.has_good() and not self.has_better() and not self.has_best()

    def has_good(self):
        return not_empty(self.good)
    
    def has_better(self):
        return not_empty(self.better)
    
    def has_best(self):
        return not_empty(self.best)
    
    def good_list(self):
        return listize(self.good)
    
    def better_list(self):
        return listize(self.better)
    
    def best_list(self):
        return listize(self.best)

Event = Union[
    JournalAdded, 
    HabitTracked, 
    ObservationMade, 
    ObservationUpdated, 
    ObservationRecontextualized, 
    ObservationReinterpreted, 
    ObservationReflectedUpon, 
    ObservationClosed
]

class Result(BaseModel):
    date: date
    events: List[Event]
    plan: Optional[Plan]
    reflection: Optional[Reflection]

    def empty(self):
        if self.events:
            return False
        
        if self.plan and not self.plan.empty():
            return False
        
        if self.reflection and not self.reflection.empty():
            return False
        
        return True


def parse_result(result_data: dict) -> Result:
    return Result.model_validate(result_data)


def get_daily_events(config: TasksConfigFile, arguments: dict, dt: date = None):
    if dt is None:
        dt = datetime.now().date()
    
    dt_string = '?date={}'.format(dt.strftime('%Y-%m-%d'))

    url = '{}/api/events/daily/{}'.format(
        config.url, 
        dt_string,
    )

    auth = HTTPBasicAuth(config.user, config.password)

    r = requests.get(url, auth=auth)

    out = r.json()

    if not r.ok:
        raise RuntimeError("{}: {}".format(r.status_code, str(out)))

    return parse_result(out)


def do_fill(text, width=80):
    # preserve links
    if any(a in text for a in ('](', 'http://', 'https://')):
        return text

    return fill(text, width=width)


def wrap_text_preserve_linebreaks(text, width=80):
    paragraphs = text.splitlines()
    
    wrapped_paragraphs = [do_fill(paragraph, width=width) for paragraph in paragraphs]
    
    return '\n'.join(wrapped_paragraphs)


def stats(closed, added, count):
    if closed:
        return ' (closed)'

    if added:
        return ' (added)'

    if count > 1:
        return f' ({count} updates)'

    return ''

class ObservationStatistics:
    added: set
    closed: set
    all: set

    renders: dict
    counter: Counter
    count: int
    def __init__(self, observations: List[ObservationEvent]):
        self.added = set()
        self.closed = set()
        self.all = set()
        self.counter = Counter()
        self.situation_fields = {}
        self.renders = {}
        self.count = len(observations)
        self.urls = {}
        for observation in observations:
            self.counter[observation.event_stream_id] += 1
            self.all.add(observation.event_stream_id)

            if isinstance(observation, ObservationMade):
                self.added.add(observation.event_stream_id)
            elif isinstance(observation, ObservationClosed):
                self.closed.add(observation.event_stream_id)

            if hasattr(observation, 'url'):
                self.urls[observation.event_stream_id] = observation.url

            if hasattr(observation, 'situation'):
                self.situation_fields[observation.event_stream_id] = observation.situation
            elif hasattr(observation, 'situation_at_creation'):
                self.situation_fields[observation.event_stream_id] = observation.situation_at_creation

        for id in self.all:
            _stats = stats(
                id in self.closed, 
                id in self.added, 
                self.counter[id]
            )

            self.renders[id] = '- [{situation}]({url}){updates}'.format(
                situation=first_line(self.situation_fields[id]),
                url=self.urls[id],
                updates=_stats
            )

    def get_context(self):
        return {
            'count': self.count,
            'renders': '\n'.join(self.renders.values()),
        }

def render_daily_events(result: Result):
    observations = [event for event in result.events if isinstance(event, ObservationEvent)]
    observation_stats = ObservationStatistics(observations)

    dct = {
        'date': result.date.strftime('%-d %B (%A)'),
        'habits': '\n'.join(event.render() for event in result.events if isinstance(event, HabitTracked)),
        'events': '\n'.join(event.render() for event in result.events if isinstance(event, JournalAdded)),
        'plan': result.plan,
        'reflection': result.reflection,
        'observation_stats': observation_stats.get_context(),
    }

    rendered = render_template(TEMPLATE, dct)

    return wrap_text_preserve_linebreaks(rendered)


def save_to_file(directory: Path, dt: date, rendered: str):
    file_path = directory / f'{dt.strftime("%m-%B").lower()}.md'
    
    with open(file_path, 'a') as f:
        f.write(rendered)


def delete_file_if_needed(already_deleted: set,directory: Path, dt: date):
    file_path = directory / f'{dt.strftime("%m-%B").lower()}.md'
    
    if file_path.exists() and file_path not in already_deleted:
        file_path.unlink()
        already_deleted.add(file_path)

def main():
    arguments = docopt(__doc__, version=VERSION)

    path = arguments['PATH']

    if path:
        directory = Path(path).resolve(strict=True)
    
    config = TasksConfigFile()

    year = int(arguments['--year']) if arguments['--year'] else None

    if year:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
    else:
        start_date = parse(arguments['--from']).date() if arguments['--from'] else datetime.now().date()
        end_date = parse(arguments['--to']).date() if arguments['--to'] else start_date

    def date_range(start_date, end_date, delta):
        current_date = start_date
        while current_date <= end_date:
            yield current_date
            current_date += delta

    already_deleted = set()

    for dt in date_range(start_date, end_date, timedelta(days=1)):
        if path:
            print("Processing... {}".format(dt), "\r", end='')

        result = get_daily_events(config, arguments, dt)

        if result.empty():
            continue

        rendered = render_daily_events(result)

        if path:
            delete_file_if_needed(already_deleted, directory, dt)
            save_to_file(directory, dt, rendered)
        else:
            print(rendered)
    
    if path:
        print("\nDone.")


