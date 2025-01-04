import sys
import contextlib

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
