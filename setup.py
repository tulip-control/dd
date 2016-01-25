import logging
import sys
from setuptools import setup
import download
# inline:
# from dd import _parser, dddmp
# import git


name = 'dd'
description = (
    'Library of decision diagrams and algorithms on them, '
    'in pure Python, as well as Cython bindings to CUDD and BuDDy.')
url = 'https://github.com/johnyf/{name}'.format(name=name)
README = 'README.md'
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 2
MICRO = 2
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
    'setuptools >= 19.6']
if sys.version_info.major < 3:
    pydot_require = 'pydot >= 1.0.28'
else:
    pydot_require = 'pydot3k >= 1.0.17'
extras_require = dict(
    dot=pydot_require)
tests_require = [
    'nose >= 1.3.4',
    pydot_require]
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
    try:
        import git
        repo = git.Repo('.git')
    except ImportError:
        print('gitpython not found: Assume release.')
        return ''
    try:
        repo.git.status()
    except git.GitCommandNotFound:
        print('git not found: Assume release.')
        return ''
    sha = repo.head.commit.hexsha
    if repo.is_dirty():
        return '.dev0+{sha}.dirty'.format(sha=sha)
    # commit is clean
    # is it release of `version` ?
    try:
        tag = repo.git.describe(
            match='v[0-9]*', exact_match=True,
            tags=True, dirty=True)
        assert tag[1:] == version, (tag, version)
        return ''
    except git.GitCommandError:
        return '.dev0+{sha}'.format(sha=sha)


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
    # version
    version = VERSION + git_version(VERSION)
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
        extras_require=extras_require,
        tests_require=tests_require,
        packages=[name],
        package_dir={name: name},
        ext_modules=ext_modules,
        classifiers=classifiers,
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
