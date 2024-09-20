import requests
from requests.auth import HTTPBasicAuth


def quick_note_to_string(note):
    return "\n  ".join(note['note'].split("\n"))


def _get_quick_notes_as_string(config):
    try:
        url = '{}/quick-notes/'.format(config.url)

        r = requests.get(url, auth=HTTPBasicAuth(config.user, config.password))

        if not r.ok:
            return ''
        
        j = r.json()

        return "\n- ".join(map(quick_note_to_string, j['results']))
        
    except ConnectionError:
        pass

    return ''


def get_quick_notes_as_string(config):
    quick_notes =  _get_quick_notes_as_string(config)

    if len(quick_notes) > 0:
        quick_notes = "\n- {}\n".format(quick_notes)

    return quick_notes