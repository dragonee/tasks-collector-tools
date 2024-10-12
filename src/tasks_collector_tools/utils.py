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