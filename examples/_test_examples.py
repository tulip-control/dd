"""Run each example module."""
import os
import subprocess as _sbp
import sys


def _main(
        ) -> None:
    """Run each example module under `.`."""
    _, _, files = next(os.walk('.'))
    this_file = os.path.basename(__file__)
    files.remove(this_file)
    for filename in files:
        _, ext = os.path.splitext(filename)
        if ext != '.py':
            continue
        cmd = [sys.executable, filename]
        print(cmd)
        retcode = _sbp.call(cmd)
        if retcode == 0:
            continue
        raise RuntimeError(retcode)


if __name__ == '__main__':
    _main()
