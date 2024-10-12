import sys
import contextlib

@contextlib.contextmanager
def smart_open(filename=None, *args, pipe=sys.stdin, **kwargs):
    if filename and filename != '-':
        fh = open(filename, *args, **kwargs)
    else:
        fh = pipe

    try:
        yield fh
    finally:
        if fh is not sys.stdout:
            fh.close()


def sanitize_string(value):
    return value.strip().replace('\n', '\r\n') if value else None


def sanitize_fields(payload):
    return {k: sanitize_string(v) for k, v in payload.items()}


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
