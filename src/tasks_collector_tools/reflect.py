"""Reflect on a day, week or month.

Usage: 
    reflect [options]

Options:
    -d, --date DATE  Use this date for reflection.
    -w, --week       Use this week for reflection.
    -m, --month      Use this month for reflection.
    -y, --yesterday  Use yesterday for reflection.
    -M, --missing    Fill in missing journal entries for the date range.
    -h, --help       Show this message.
    --version        Show version information.
"""

import os, re, sys

from docopt import docopt

from datetime import datetime, date, timedelta

import tempfile

import subprocess

from pydantic import BaseModel, Field
from typing import List

from .utils import get_cursor_position

from datetime import timezone

from dateutil.parser import parse

import calendar

from pprint import pprint

def get_start_and_end_of_week(date):
    # Calculate start of week (Monday) and end of week (Sunday) using timedelta
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end


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


title_re = re.compile(r'^##? (Reflection|Better|Best)')


empty_point_re = re.compile(r'^\s*\-\s*(?:\[\s+\])\s*')
point_re = re.compile(r'^\s*\-\s*(?:\[x\^\~\])?\s*')

def add_stack_to_payload(payload, name, lines):
    if name is None:
        return

    if name == 'Reflection':
        name = 'good'

    payload[name.lower()] = ''.join(lines).strip()


multi_line_re = re.compile(r'\n(\s*\n)+')


JOURNAL_TEMPLATE = """
{good}

{better}

{best} 
"""

class JournalPayload(BaseModel):
    """Pydantic model for journal payload."""
    published: str
    comment: str
    thread: str
    tags: List[str] = Field(default_factory=list)
    reflection: bool = False
    
    def to_journal_command(self) -> List[str]:
        """Convert the payload into journal command arguments."""
        cmd = ['journal']
        
        if self.thread:
            cmd.extend(['--thread', self.thread])
            
        if self.published:
            cmd.extend(['--date', self.published])
        
        if self.tags:
            cmd.extend(['--tags', ', '.join(self.tags)])
            
        return cmd


def journal_payload_from_reflection_payload(
        payload: dict, 
        published: datetime, 
        thread: str
    ) -> JournalPayload:
    comment = JOURNAL_TEMPLATE.format(**payload).strip()
    comment = multi_line_re.sub('\n\n', comment)

    return JournalPayload(
        published=published.isoformat(),
        comment=comment,
        thread=thread,
        tags=[],
        reflection=True,
    )


def published_from_arguments(arguments):
    dt = datetime.now()

    if arguments['--date']:
        dt = parse(arguments['--date'])
    
    if arguments['--yesterday']:
        return datetime.now() - timedelta(days=1)
    elif arguments['--week']:
        _, end = get_start_and_end_of_week(dt)
        
        return end.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=timezone.utc)
    elif arguments['--month']:
        _, end = get_start_and_end_of_month(dt)

        return end.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=timezone.utc)
    
    return dt


def fill_missing_journal_entries(arguments):
    """Fill in missing journal entries for the specified date range."""
    cmd = ['reflectiondump', '-M']

    day = parse(arguments['--date']) if arguments['--date'] else date.today()

    thread = get_fetch_thread_from_arguments(arguments)
    if thread is not None:
        cmd += ['--thread', thread]

    if arguments['--week']:
        start, end = get_start_and_end_of_week(day)
    elif arguments['--month']:
        start, end = get_start_and_end_of_month(day)
    elif arguments['--yesterday']:
        start = end = day - timedelta(days=1)
    else:
        start = end = day

    cmd += [
        '-d', start.strftime('%Y-%m-%d'),
        '-D', end.strftime('%Y-%m-%d'),
    ]

    try:
        output = subprocess.check_output(cmd).decode('utf-8').strip()
        
        if not output:
            return
        
        missing_dates = list(map(lambda x: x.strip(), output.split('\n')))
        print(f"Found {len(missing_dates)} missing journal entries.")
        
        for date_str in missing_dates:
            date_str_formatted = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d (%A)')
            print(f"Creating journal entry for {date_str_formatted}...")

            journal_cmd = ['journal', '--date', date_str]
            
            try:
                subprocess.run(journal_cmd, check=True)
            except subprocess.CalledProcessError:
                print(f"Error creating journal entry for {date_str}")
    except subprocess.CalledProcessError as e:
        print(f"Error running reflectiondump: {e}")


def main():
    arguments = docopt(__doc__, version='1.1')
    
    if arguments['--missing']:
        fill_missing_journal_entries(arguments)

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

    os.unlink(tmpfile.name)

    if not payload['good']:
        print("No changes were made to the Comment field.")

        sys.exit(0)

    published = published_from_arguments(arguments)

    thread = get_save_thread_from_arguments(arguments)

    payload = journal_payload_from_reflection_payload(payload, published, thread)

    cmd = payload.to_journal_command()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md') as f:
        f.write(payload.comment)
        f.flush()

        cmd.extend(['--file', f.name])

        subprocess.run(cmd, check=True)

        
            

            
