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