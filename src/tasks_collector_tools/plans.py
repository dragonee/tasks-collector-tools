import requests

from datetime import date

from dataclasses import dataclass

from .utils import itemize_string

FOCUS_TEMPLATE = "Focus: {focus}"
WANT_TEMPLATE = "Want: {want}"

PLAN_TEMPLATE = """
{focus}
{want}
"""

@dataclass
class Plan:
    id: int
    pub_date: date
    focus: str
    want: str

    def __str__(self):
        focus = itemize_string(self.focus, prepend="\n")
        want = itemize_string(self.want, prepend="\n")

        if focus.strip():
            focus = FOCUS_TEMPLATE.format(focus=focus)
        
        if want.strip():
            want = WANT_TEMPLATE.format(want=want)

        return PLAN_TEMPLATE.format(focus=focus, want=want).strip() + "\n"


def get_plan_for_today(config):
    url = '{}/plans/?pub_date={}'.format(config.url, date.today().isoformat())

    response = requests.get(url, auth=(config.user, config.password))
    response.raise_for_status()

    data = response.json()

    if data['count'] == 0:
        return None

    return Plan(**data['results'][0])