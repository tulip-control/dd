import logging
import sys
from setuptools import setup
import download
# inline:
# from dd import _parser, dddmp


name = 'dd'
description = 'Library of decision diagrams and algorithms on them.'
url = 'https://github.com/johnyf/{name}'.format(name=name)
README = 'README.md'
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 1
MICRO = 1
version = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
s = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n").format(version=version)
install_requires = [
    'astutils >= 0.0.1',
    'networkx >= 1.9.1',
    'ply >= 3.4']
extras_require = dict(
    dot='pydot >= 1.0.28')
tests_require = [
    'nose >= 1.3.4',
    'pydot >= 1.0.28']


def run_setup(with_ext):
    # install build deps ?
    if '--fetch' in sys.argv:
        sys.argv.remove('--fetch')
        download.fetch_cudd()
    # build extensions ?
    e = list()
    for opt in ('--cudd', '--buddy'):
        if opt in sys.argv:
            e.append(opt[2:])
            sys.argv.remove(opt)
    # default
    if not e:
        e.append('cudd')
    if not with_ext:
        e = list()
    extensions = download.extensions()
    ext_modules = list(extensions[k] for k in e)
    # build parsers
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
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
        extras_require=extras_require,
        tests_require=tests_require,
        packages=[name],
        package_dir={name: name},
        ext_modules=ext_modules,
        keywords=[
            'bdd', 'binary decision diagram', 'decision diagram',
            'boolean', 'networkx', 'dot'])


if __name__ == '__main__':
    with_ext = False
    for opt in ('--fetch', '--cudd', '--buddy'):
        if opt in sys.argv:
            with_ext = True
    try:
        run_setup(with_ext=True)
    except:
        print('WARNING: `dd` failed to compile C extensions.')
        run_setup(with_ext=with_ext)
