from functools import wraps
from textwrap import dedent
import sys


def entrypoint(func):
    @wraps(func)
    def invocation():
        try:
            assert len(sys.argv) <= 1 or sys.argv[1] not in {"-h", "--help"}
            return func()
        except AssertionError as ae:
            print(dedent("    " + func.__doc__))
            return 2
    return invocation
