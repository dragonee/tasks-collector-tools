import requests

from datetime import date

from dataclasses import dataclass

from .utils import itemize_string

from requests.exceptions import ConnectionError


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
        if not self.focus and not self.want:
            return ""

        focus = itemize_string(self.focus, prepend="\n", prefix="- [ ] ")
        want = itemize_string(self.want, prepend="\n", prefix="- [ ] ")

        if focus.strip():
            focus = FOCUS_TEMPLATE.format(focus=focus)
        
        if want.strip():
            want = WANT_TEMPLATE.format(want=want)

        return PLAN_TEMPLATE.format(focus=focus, want=want).strip() + "\n"


def get_plan_for_today(config):
    try:
        url = '{}/plans/?pub_date={}&thread=Daily'.format(config.url, date.today().isoformat())

        response = requests.get(url, auth=(config.user, config.password))
        response.raise_for_status()

        data = response.json()

        if data['count'] == 0:
            return Plan(id=None, pub_date=date.today(), focus="", want="")

        return Plan(**data['results'][0])
    except ConnectionError:
        return Plan(id=None, pub_date=date.today(), focus='', want='')