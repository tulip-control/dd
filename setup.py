import logging
from setuptools import setup
# inline:
# from dd import bdd, dddmp


name = 'dd'
description = 'Library of decision diagrams and algorithms on them.'
url = 'https://github.com/johnyf/{name}'.format(name=name)
README = 'README.md'
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 0
MICRO = 4
version = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
s = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n").format(version=version)
install_requires = [
    'astutils >= 0.0.1',
    'networkx >= 1.9.1',
    'ply >= 3.4']
extras_require = {
    'dot': 'pydot >= 1.0.28'}
tests_require = [
    'nose >= 1.3.4',
    'pydot >= 1.0.28']


if __name__ == '__main__':
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
    try:
        from dd import bdd, dddmp
        logging.getLogger('astutils').setLevel('ERROR')
        dddmp._rewrite_tables(outputdir=name)
        bdd._rewrite_tables(outputdir=name)
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
        keywords=[
            'bdd', 'binary decision diagram', 'decision diagram',
            'boolean', 'networkx', 'dot'])
