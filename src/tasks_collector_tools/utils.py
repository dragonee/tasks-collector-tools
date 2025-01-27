import sys
import contextlib
import re

SHORT_TIMEOUT = 3.05

@contextlib.contextmanager
def smart_open(filename=None, mode='r', pipe=None, **kwargs):
    if filename and filename != '-':
        fh = open(filename, mode=mode, **kwargs)
    elif pipe is not None:
        fh = pipe
    else:
        fh = sys.stdin if mode.startswith('r') else sys.stdout

    try:
        yield fh
    finally:
        if fh not in (sys.stdout, sys.stderr, sys.stdin):
            fh.close()


def sanitize_string(value):
    return value.strip().replace('\n', '\r\n') if value else None

def sanitize_list_of_strings(value):
    return list(filter(None, map(str.strip, value)))

def sanitize_fields(payload, mapping=None):
    mapping = mapping or {}

    return {k: mapping.get(k, sanitize_string)(v) for k, v in payload.items()}


def itemize_string(value, prepend=None, append=None, prefix="- "):
    s = "\n".join([prefix + line.strip() if line.strip() else line for line in value.split("\n")])

    if prepend:
        s = prepend + s

    if append:
        s = s + append

    return s

def get_cursor_position(template, search_string):
    comment_index = template.find(search_string)
    if comment_index != -1:
        newlines_before_comment = template[:comment_index].count('\n')
    else:
        newlines_before_comment = 0

    return newlines_before_comment + 3


def _get_value(obj, key):
    if isinstance(obj, dict):
        return obj[key]
    if isinstance(obj, list):
        return obj[int(key)]
    if callable(obj):
        return obj(key)
    attr = getattr(obj, key)
    if callable(attr):
        return attr()
    return attr


def getter(obj, key: tuple[str, ...], default=None):
    item = _get_value(obj, key[0])

    if item is None:
        return default

    if len(key) == 1:
        return item
    
    return getter(item, key[1:])


def render_template(template, context):
    def replace_var(match):
        var_name = match.group(1)
        return str(getter(context, var_name.split('.'), default=''))

    def eval_if(match):
        condition = match.group(1)
        true_part = match.group(2)
        try:
            false_part = match.group(3)
        except IndexError:
            false_part = ''
        return true_part if getter(context, condition.split('.')) else false_part

    template = re.sub(r'\{% if (.*?) %\}(.*?)\{% else %\}(.*?)\{% endif %\}', eval_if, template, flags=re.DOTALL)
    template = re.sub(r'\{% if (.*?) %\}(.*?)\{% endif %\}', eval_if, template, flags=re.DOTALL)
    template = re.sub(r'\{\{ (.*?) \}\}', replace_var, template)
    template = re.sub(r'\n\s*\n\s*\n', '\n\n', template)

    return template