"""Installation script."""
import argparse
import logging
import sys

from setuptools import setup
from pkg_resources import parse_version

import download
# inline:
# from dd import _parser, dddmp
# import git


name = 'dd'
description = (
    'Library of decision diagrams and algorithms on them, '
    'in pure Python, as well as Cython bindings to '
    'CUDD, Sylvan, and BuDDy.')
url = 'https://github.com/johnyf/{name}'.format(name=name)
README = 'README.md'
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 5
MICRO = 0
VERSION = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
VERSION_TEXT = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n")
install_requires = [
    'astutils >= 0.0.1',
    'networkx >= 1.9.1',
    'ply >= 3.4',
    'psutil >= 3.2.2',
    'pydot >= 1.2.2',
    'setuptools >= 19.6']
tests_require = [
    'nose >= 1.3.4']
classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Cython',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering',
    'Topic :: Software Development']


def git_version(version):
    """Return version with local version identifier."""
    import git
    repo = git.Repo('.git')
    repo.git.status()
    # assert versions are increasing
    latest_tag = repo.git.describe(
        match='v[0-9]*', tags=True, abbrev=0)
    assert parse_version(latest_tag) <= parse_version(version), (
        latest_tag, version)
    sha = repo.head.commit.hexsha
    if repo.is_dirty():
        return '{v}.dev0+{sha}.dirty'.format(
            v=version, sha=sha)
    # commit is clean
    # is it release of `version` ?
    try:
        tag = repo.git.describe(
            match='v[0-9]*', exact_match=True,
            tags=True, dirty=True)
    except git.GitCommandError:
        return '{v}.dev0+{sha}'.format(
            v=version, sha=sha)
    assert tag == 'v' + version, (tag, version)
    return version


def parse_args():
    """Return `args` irrelevant to `setuptools`."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--fetch', action='store_true',
        help='download cudd from its website')
    parser.add_argument(
        '--linetrace', action='store_true',
        help='use line tracing for Cython extensions')
    for opt in download.EXTENSIONS:
        parser.add_argument(
            '--{s}'.format(s=opt), default=None,
            const='', type=str, nargs='?',
            help='build Cython extension {s}'.format(s=opt))
    args, unknown = parser.parse_known_args()
    # avoid confusing `setuptools`
    sys.argv = [sys.argv[0]] + unknown
    return args


def run_setup():
    """Build parser, get version from `git`, install."""
    args = parse_args()
    if args.fetch:
        download.fetch_cudd()
    # build extensions ?
    ext_modules = download.extensions(args)
    # version
    try:
        version = git_version(VERSION)
    except AssertionError:
        raise
    except:
        print('No git info: Assume release.')
        version = VERSION
    s = VERSION_TEXT.format(version=version)
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
    # build parsers
    try:
        from dd import _parser, dddmp
        logging.getLogger('astutils').setLevel('ERROR')
        dddmp._rewrite_tables(outputdir=name)
        _parser._rewrite_tables(outputdir=name)
    except ImportError:
        print('WARNING: `dd` could not cache parser tables '
              '(ignore this if running only for "egg_info").')
    setup(
        name=name,
        version=version,
        description=description,
        long_description=open(README).read(),
        author='Ioannis Filippidis',
        author_email='jfilippidis@gmail.com',
        url=url,
        license='BSD',
        install_requires=install_requires,
        tests_require=tests_require,
        packages=[name],
        package_dir={name: name},
        ext_modules=ext_modules,
        classifiers=classifiers,
        keywords=[
            'bdd', 'binary decision diagram', 'decision diagram',
            'boolean', 'networkx', 'dot'])


if __name__ == '__main__':
    run_setup()
