"""Discover random events and create discoveries.

Usage:
    discovery [options]

Options:
    -n, --number NUM     Number of events to fetch [default: 3]
    -f, --from DATE      Start date for event range
    -t, --to DATE        End date for event range
    --type TYPE          Event types (journal, observation, other) [default: all]
    -h, --help           Show this message.
    --version            Show version information.
"""

import json
import os
import re
import sys
import tempfile
import subprocess

from docopt import docopt
from datetime import datetime, timedelta
from dateutil.parser import parse

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError

from .config.tasks import TasksConfigFile
from .utils import queue_failed_request, retry_failed_requests


TEMPLATE = """
# Discovery ({published})

## Name

Discovery name here

## Thread

Daily

## Comment

Discovery details here

"""

def fetch_events(config, number=3, locked_events=None, from_date=None, to_date=None, event_types=None):
    """Fetch events from the discovery API endpoint."""
    url = f"{config.url}/api/events/discovery/"

    payload = {
        'number': number
    }

    if locked_events:
        payload['events'] = locked_events

    if from_date:
        payload['from'] = from_date.isoformat()

    if to_date:
        payload['to'] = to_date.isoformat()

    if event_types and event_types != 'all':
        payload['type'] = event_types.split(',')

    r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))

    if r.ok:
        return r.json()
    else:
        try:
            sys.stderr.write(json.dumps(r.json(), indent=4, sort_keys=True) + '\n')
        except json.decoder.JSONDecodeError:
            sys.stderr.write(f"HTTP {r.status_code}\n{r.text}\n")
        return None


def format_event(index, event):
    """Format an event for display."""
    event_type = event.get('resourcetype', 'Unknown')
    event_id = event.get('id', 'N/A')
    published = event.get('published', 'N/A')

    lines = [f"\n[{index}] Event #{event_id} ({event_type})"]
    lines.append(f"    Published: {published}")

    if event_type == 'HabitTracked':
        habit = event.get('habit', {})
        habit_name = habit.get('name', 'Unknown')
        occured = event.get('occured', False)
        note = event.get('note', '')

        lines.append(f"    Habit: {habit_name} ({'✓' if occured else '✗'})")
        if note:
            lines.append(f"    Note: {note}")

    elif event_type == 'JournalAdded':
        thread = event.get('thread', 'Unknown')
        comment = event.get('comment', '')

        lines.append(f"    Thread: {thread}")
        if comment:
            # Show first line of comment
            first_line = comment.split('\n')[0][:60]
            lines.append(f"    Comment: {first_line}...")

    elif event_type == 'ObservationClosed':
        thread = event.get('thread', 'Unknown')
        situation = event.get('situation', '')

        lines.append(f"    Thread: {thread}")
        if situation:
            first_line = situation.split('\n')[0][:60]
            lines.append(f"    Situation: {first_line}...")

    elif event_type == 'ObservationMade':
        thread = event.get('thread', 'Unknown')
        situation = event.get('situation', '')

        lines.append(f"    Thread: {thread}")
        if situation:
            first_line = situation.split('\n')[0][:60]
            lines.append(f"    Situation: {first_line}...")

    return '\n'.join(lines)


def display_events(events, locked_indices):
    """Display all events with lock indicators."""
    for i, event in enumerate(events, 1):
        lock_marker = "🔒 " if i in locked_indices else ""
        print(lock_marker + format_event(i, event))
    print()


def build_template_from_events(events):
    """Build editor template with event contents."""
    lines = [
        "# Discovery ({})".format(datetime.now()),
        "",
        "## Name",
        "",
        "Discovery name here",
        "",
        "## Thread",
        "",
        "Daily",
        "",
        "## Comment",
        "",
    ]

    for i, event in enumerate(events, 1):
        event_type = event.get('resourcetype', 'Unknown')
        event_id = event.get('id', 'N/A')

        lines.append(f"### Event {i}: {event_type} (#{event_id})")
        lines.append("")

        if event_type == 'HabitTracked':
            habit = event.get('habit', {})
            habit_name = habit.get('name', 'Unknown')
            occured = event.get('occured', False)
            note = event.get('note', '')

            lines.append(f"**Habit:** {habit_name} ({'occurred' if occured else 'did not occur'})")
            if note:
                lines.append(f"**Note:** {note}")

        elif event_type == 'JournalAdded':
            thread = event.get('thread', 'Unknown')
            comment = event.get('comment', '')

            lines.append(f"**Thread:** {thread}")
            if comment:
                lines.append(f"**Comment:**")
                lines.append(f"```")
                lines.append(comment)
                lines.append(f"```")

        elif event_type in ['ObservationClosed', 'ObservationMade']:
            thread = event.get('thread', 'Unknown')
            situation = event.get('situation', '')
            interpretation = event.get('interpretation', '')
            approach = event.get('approach', '')

            lines.append(f"**Thread:** {thread}")
            if situation:
                lines.append(f"**Situation:** {situation}")
            if interpretation:
                lines.append(f"**Interpretation:** {interpretation}")
            if approach:
                lines.append(f"**Approach:** {approach}")

        lines.append("")

    return '\n'.join(lines) + '\n'


def parse_discovery_file(filepath):
    """Parse the edited discovery file."""
    name_re = re.compile(r'^## Name')
    thread_re = re.compile(r'^## Thread')
    comment_re = re.compile(r'^## Comment')

    payload = {
        'name': None,
        'thread': None,
        'comment': None
    }

    with open(filepath) as f:
        current_section = None
        current_stack = []

        for line in f:
            if name_re.match(line):
                if current_section is not None and current_stack:
                    payload[current_section] = ''.join(current_stack).strip()
                current_section = 'name'
                current_stack = []
            elif thread_re.match(line):
                if current_section is not None and current_stack:
                    payload[current_section] = ''.join(current_stack).strip()
                current_section = 'thread'
                current_stack = []
            elif comment_re.match(line):
                if current_section is not None and current_stack:
                    payload[current_section] = ''.join(current_stack).strip()
                current_section = 'comment'
                current_stack = []
            elif line.startswith('#'):
                # Skip other headers
                continue
            else:
                if current_section:
                    current_stack.append(line)

        if current_section is not None and current_stack:
            payload[current_section] = ''.join(current_stack).strip()

    return payload


def create_discovery(config, name, thread, comment, event_ids):
    """Create a discovery via POST /discoveries/."""
    url = f"{config.url}/discoveries/"

    payload = {
        'name': name,
        'thread': thread,
        'comment': comment,
        'event_ids': event_ids
    }

    try:
        retry_failed_requests(metadata={
            'auth': HTTPBasicAuth(config.user, config.password)
        })
    except Exception as e:
        print(e)
        print("Error: Failed to send queue")

    try:
        r = requests.post(url, json=payload, auth=HTTPBasicAuth(config.user, config.password))
    except ConnectionError:
        name_file = queue_failed_request(payload, metadata={
            'url': url,
        }, file_type="discovery")

        print("Error: Connection failed.")
        print(f"Your discovery was saved at {name_file}.")
        print("It will be sent next time you run this program.")

        sys.exit(2)

    if r.ok:
        discovery = r.json()
        print("\nDiscovery created successfully!")
        print(f"Name: {discovery.get('name')}")
        print(f"Thread: {discovery.get('thread')}")
        if 'id' in discovery:
            print(f"ID: {discovery['id']}")
        return True
    else:
        try:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        except json.decoder.JSONDecodeError:
            print(f"HTTP {r.status_code}\n{r.text}")
        return False


def interactive_discovery(config, number, from_date, to_date, event_types):
    """Run the interactive discovery shell."""
    locked_indices = set()
    events = []

    # Initial fetch
    result = fetch_events(config, number, from_date=from_date, to_date=to_date, event_types=event_types)
    if not result:
        print("Error: Could not fetch events")
        return

    events = result.get('events', [])

    print("\nDiscovery Shell")
    print("Commands:")
    print("  1-9: Lock/unlock event")
    print("  r: Reroll unlocked events")
    print("  c: Create discovery from current events")
    print("  q: Quit")
    print()

    display_events(events, locked_indices)

    while True:
        try:
            command = input("> ").strip().lower()

            if command == 'q':
                print("Goodbye!")
                break

            elif command == 'r':
                # Reroll unlocked events
                locked_events = [None] * number
                for idx in locked_indices:
                    if 1 <= idx <= number:
                        locked_events[idx - 1] = events[idx - 1]['id']

                result = fetch_events(config, number, locked_events, from_date, to_date, event_types)
                if result:
                    events = result.get('events', [])
                    display_events(events, locked_indices)
                else:
                    print("Error: Could not fetch events")

            elif command == 'c':
                # Create discovery
                if not events:
                    print("No events to create discovery from")
                    continue

                # Create temp file with event contents
                tmpfile = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
                template = build_template_from_events(events)

                with tmpfile:
                    tmpfile.write(template)

                editor = os.environ.get('EDITOR', 'vim')
                result = subprocess.run([editor, '+5', tmpfile.name])

                if result.returncode != 0:
                    print("Editor exited with error")
                    os.unlink(tmpfile.name)
                    continue

                # Parse the file
                parsed = parse_discovery_file(tmpfile.name)

                if not parsed['name'] or parsed['name'] == 'Discovery name here':
                    print("Error: Please provide a discovery name")
                    print(f"Temporary file saved at: {tmpfile.name}")
                    continue

                # Create discovery with event IDs
                event_ids = [event['id'] for event in events]

                success = create_discovery(
                    config,
                    parsed['name'],
                    parsed['thread'] or 'Daily',
                    parsed['comment'] or '',
                    event_ids
                )

                if success:
                    os.unlink(tmpfile.name)
                    break
                else:
                    print(f"Temporary file saved at: {tmpfile.name}")

            elif command.isdigit():
                idx = int(command)
                if 1 <= idx <= number:
                    if idx in locked_indices:
                        locked_indices.remove(idx)
                        print(f"Unlocked event {idx}")
                    else:
                        locked_indices.add(idx)
                        print(f"Locked event {idx}")
                    display_events(events, locked_indices)
                else:
                    print(f"Invalid event number. Choose 1-{number}")

            else:
                print("Unknown command. Use 1-9, r, c, or q")

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


def main():
    arguments = docopt(__doc__, version='1.0.0')

    config = TasksConfigFile()

    number = int(arguments['--number'])
    if number < 1 or number > 100:
        print("Error: Number must be between 1 and 100")
        sys.exit(1)

    from_date = parse(arguments['--from']) if arguments['--from'] else None
    to_date = parse(arguments['--to']) if arguments['--to'] else None
    event_types = arguments['--type']

    interactive_discovery(config, number, from_date, to_date, event_types)


if __name__ == '__main__':
    main()
