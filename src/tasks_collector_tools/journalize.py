"""Convert observationupdate to journal.

Usage:
    journalize [options] OBSERVATION_ID

Options:
    -h, --help       Show this message.
    --version        Show version information. 
"""

VERSION = '1.0'


from docopt import docopt

from .config.tasks import TasksConfigFile

import requests

from urllib.parse import urlencode

def get_observation(config, observation_id: int):
    url = '{}/observation-api/{}/?features=updates'.format(
        config.url,
        observation_id,
    )

    auth = (config.user, config.password)

    response = requests.get(url, auth=auth)
    response.raise_for_status()

    return response.json()

def add_journal(config, update, observation):
    url = f'{config.url}/journal/'
    auth = (config.user, config.password)

    payload = {
        'published': update['published'],
        'comment': update['comment'],
        'thread': observation['thread'],
    }

    response = requests.post(url, json=payload, auth=auth)
    response.raise_for_status()


def delete_observation(config, observation_id: int):
    url = '{}/observation-api/{}/'.format(config.url, observation_id)
    auth = (config.user, config.password)

    response = requests.delete(url, auth=auth)
    response.raise_for_status()


def main():
    args = docopt(__doc__, version=VERSION)

    config = TasksConfigFile()

    observation_id = int(args['OBSERVATION_ID'])

    observation = get_observation(config, observation_id)
    
    for update in observation['updates']:
        add_journal(config, update, observation)
    
    delete_observation(config, observation_id)


