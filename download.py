"""Retrieve and build dependencies of C extensions."""
import collections.abc as _abc
import ctypes
import functools as _ft
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import textwrap as _tw
import typing as _ty
import urllib.error
import urllib.request


try:
    import cysignals
except ImportError:
    cysignals = None
try:
    from Cython.Build import cythonize
    pyx = '.pyx'
except ImportError:
    print('`import cython` failed')
    pyx = '.c'
from setuptools.extension import Extension


EXTENSIONS = ['cudd', 'cudd_zdd', 'buddy', 'sylvan']
# CUDD
CUDD_VERSION = '3.0.0'
CUDD_TARBALL = f'cudd-{CUDD_VERSION}.tar.gz'
CUDD_URL = (
    'https://sourceforge.net/projects/cudd-mirror/files/'
    f'cudd-{CUDD_VERSION}.tar.gz/download')
CUDD_SHA256 = (
    'b8e966b4562c96a03e7fbea239729587'
    'd7b395d53cadcc39a7203b49cf7eeb69')
CC = 'gcc'
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
CUDD_PATH = os.path.join(
    FILE_PATH,
    f'cudd-{CUDD_VERSION}')
CUDD_DIRS = ['cudd', 'dddmp', 'epd', 'mtr', 'st', 'util']
CUDD_INCLUDE = ['.'] + CUDD_DIRS
CUDD_LINK = ['cudd/.libs', 'dddmp/.libs']
CUDD_LIB = ['cudd', 'dddmp']
CUDD_CFLAGS = [
    # '-arch x86_64',
    '-fPIC',
    '-std=c99',
    '-DBSD',
    '-DHAVE_IEEE_754',
    '-mtune=native', '-pthread', '-fwrapv',
    '-fno-strict-aliasing',
    '-Wall', '-W', '-O3']
sizeof_long = ctypes.sizeof(ctypes.c_long)
sizeof_void_p = ctypes.sizeof(ctypes.c_void_p)
CUDD_CFLAGS.extend([
    f'-DSIZEOF_LONG={sizeof_long}',
    f'-DSIZEOF_VOID_P={sizeof_void_p}'])
# add -fPIC
XCFLAGS = (
    'XCFLAGS=-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD '
    f'-DSIZEOF_VOID_P={sizeof_void_p} '
    f'-DSIZEOF_LONG={sizeof_long}')
# Sylvan
SYLVAN_PATH = os.path.join(
    FILE_PATH,
    'sylvan')
SYLVAN_INCLUDE = [
    [SYLVAN_PATH, 'src'],
    [FILE_PATH, 'dd']]
SYLVAN_LINK = [[SYLVAN_PATH, 'src/.libs']]


def extensions(args):
    """Return C extensions, cythonize as needed.

    @param args: known args from `argparse.parse_known_args`
    """
    directives = dict(
        language_level=3,
        embedsignature=True)
    cudd_cflags = list(CUDD_CFLAGS)
    sylvan_cflags = list()
    # detect optional `cysignals` (unless dist)
    compile_time_env = dict(
        USE_CYSIGNALS=not (
            cysignals is None or
            args.sdist or args.bdist_wheel))
    # tell gcc to compile line tracing
    if args.linetrace:
        print('compile Cython extensions with line tracing')
        directives['linetrace'] = True
        cudd_cflags.append('-DCYTHON_TRACE=1')
        sylvan_cflags.append('-DCYTHON_TRACE=1')
        # directives['binding'] = True
    os.environ['CC'] = CC
    path = args.cudd if args.cudd else CUDD_PATH
    cudd_include = [(path, s) for s in CUDD_INCLUDE]
    cudd_link = [(path, s) for s in CUDD_LINK]
    _copy_cudd_license(args)
    _copy_extern_licenses(args)
    extensions = dict(
        cudd=Extension(
            'dd.cudd',
            sources=[f'dd/cudd{pyx}'],
            include_dirs=_join(cudd_include),
            library_dirs=_join(cudd_link),
            libraries=CUDD_LIB,
            extra_compile_args=cudd_cflags),
        cudd_zdd=Extension(
            'dd.cudd_zdd',
            sources=[f'dd/cudd_zdd{pyx}'],
            include_dirs=_join(cudd_include),
            library_dirs=_join(cudd_link),
            libraries=CUDD_LIB,
            extra_compile_args=cudd_cflags),
        buddy=Extension(
            'dd.buddy',
            sources=[f'dd/buddy{pyx}'],
            libraries=['bdd']),
        sylvan=Extension(
            'dd.sylvan',
            sources=[f'dd/sylvan{pyx}'],
            include_dirs=_join(SYLVAN_INCLUDE),
            library_dirs=_join(SYLVAN_LINK),
            libraries=['sylvan'],
            extra_compile_args=sylvan_cflags))
    for ext in EXTENSIONS:
        if getattr(args, ext) is None:
            extensions.pop(ext)
    if pyx == '.pyx':
        ext_modules = list()
        for k, v in extensions.items():
            c = cythonize(
                [v],
                compiler_directives=directives,
                compile_time_env=compile_time_env)
            ext_modules.append(c[0])
    else:
        ext_modules = list(extensions.values())
    return ext_modules


def _copy_cudd_license(args):
    """Include CUDD's license in wheels."""
    path = args.cudd if args.cudd else CUDD_PATH
    license = os.path.join(path, 'LICENSE')
    included = os.path.join('dd', 'CUDD_LICENSE')
    yes = (
        args.bdist_wheel and
        getattr(args, 'cudd') is not None)
    if yes:
        shutil.copyfile(license, included)
    elif os.path.isfile(included):
        os.remove(included)


def _copy_extern_licenses(args):
    """Include in wheels licenses related to building CUDD.

    To fetch the license files, invoke `make download_licenses`.
    """
    licenses = [
        'GLIBC_COPYING.LIB',
        'GLIBC_LICENSES',
        'PYTHON_LICENSE']
    path = os.path.join(FILE_PATH, 'extern')
    yes = (
        args.bdist_wheel and
        getattr(args, 'cudd') is not None)
    for name in licenses:
        license = os.path.join(path, name)
        included = os.path.join('dd', name)
        if yes and os.path.isfile(license):
            shutil.copyfile(license, included)
        elif yes and not os.path.isfile(license):
            print(
                f'WARNING: No file: `{license}`, '
                'skipping file copy.')
        elif os.path.isfile(included):
            os.remove(included)


def _join(
        paths:
            _abc.Iterable[
                _abc.Iterable[str]]
        ) -> list[str]:
    """Return paths, after joining each.

    Flattens a list-of-lists to a list.
    """
    return [os.path.join(*x) for x in paths]


def fetch(
        url:
            str,
        sha256:
            str,
        filename:
            str
        ) -> None:
    """Download file from `url`, and check its hashes.

    @param sha256:
        SHA-256 hash value of file that
        will be downloaded
    """
    if os.path.isfile(filename):
        print(
            f'File `{filename}` already present, '
            'checking hash.')
        _check_file_hash(filename, sha256)
        return
    print(f'Attempting to download file from URL:  {url}')
    try:
        response = urllib.request.urlopen(url)
        if response is None:
            raise urllib.error.URLError(
                '`urllib.request.urlopen` returned `None` '
                'when attempting to open the URL:  '
                f'{url}')
    except urllib.error.URLError as url_error:
        raise RuntimeError(_tw.dedent(f'''
            An exception was raised when attempting
            to open the URL:
                {url}

            In case the error message from `urllib` is
            about SSL certificates, please confirm that
            your installation of Python has the required
            SSL certificates. How to ensure this can differ,
            depending on how Python is installed
            (building from source or using an installer).

            CPython's `--with-openssl` (of `configure`)
            is relevant when building CPython from source.

            When using an installer of CPython, a separate
            post-installation step may be needed,
            as described in CPython's documentation.

            Relevant information:
                <https://www.python.org/downloads/>

            For downloading CUDD, an alternative is to
            download by other means the file at the URL:
                {url}
            unpack it, and then run:

            ```python
            import download

            download.make_cudd()
            ```

            Once CUDD compilation has completed, run:

            ```
            export DD_CUDD=1 DD_CUDD_ZDD=1;
            pip install .
            ```

            i.e., without the option `DD_FETCH`.
            ''')) from url_error
    with response, open(filename, 'wb') as f:
        f.write(response.read())
    print(
        'Completed downloading from URL '
        '(may have resulted from redirection):  '
        f'{response.url}\n'
        'Wrote the downloaded data to file:  '
        f'`{filename}`\n'
        'Will now check the hash value (SHA-256) of '
        f'the file:  `{filename}`')
    _check_file_hash(filename, sha256)


def _check_file_hash(
        filename:
            str,
        sha256:
            str
        ) -> None:
    """Assert `filename` has given hash."""
    with open(filename, 'rb') as f:
        data = f.read()
    _assert_sha(data, sha256, 256, filename)
    print(
        'Checked hash value (SHA-256) of '
        f'file `{filename}`, and is as expected.')


def _assert_sha(
        data:
            bytes,
        expected_sha_value:
            str,
        algo:
            _ty.Literal[
                256,
                512],
        filename:
            str |
            None=None
        ) -> None:
    """Assert `data` hash is `expected_sha_value`.

    If the hash of `data`, as computed using the algorithm
    specified in `algo`, is not `expected_sha_value`,
    then raise an `AssertionError`.

    The hash value is computed using the functions:
    - `hashlib.sha256()` if `algo == 256`
    - `hashlib.sha512()` if `algo == 512`

    @param data:
        bytes, to compute the hash of them
        (as accepted by `hashlib.sha512()`)
    @param expected_sha_value:
        hash value (SHA-256 or SHA-512),
        must correspond to `algo`
    @param algo:
        hashing algorithm
    @param filename:
        name of file whose hash
        is being checked, optional argument,
        if present then it will be used
        in message of the `AssertionError`
    """
    match algo:
        case 256:
            h = hashlib.sha256(data)
        case 512:
            h = hashlib.sha512(data)
        case _:
            raise ValueError(
                f'unknown algorithm:  {algo = }')
    x = h.hexdigest()
    if x == expected_sha_value:
        return
    if filename is None:
        fs = ''
    else:
        fs = f'`{filename}` '
    raise AssertionError(
        f'The computed SHA-{algo} hash value '
        f'of the downloaded file {fs}does not match '
        'the expected hash value.'
        f'\nComputed SHA-{algo}:  {x}'
        f'\nExpected SHA-{algo}:  {expected_sha_value}')


def untar(
        filename:
            str
        ) -> None:
    """Extract contents of tar file `filename`."""
    print(f'++ unpack: {filename}')
    with tarfile.open(filename) as tar:
        tar.extractall()
    print('-- done unpacking.')


def make_cudd():
    """Compile CUDD."""
    path = CUDD_PATH
    cmd = ["./configure", "CFLAGS=-fPIC -std=c99"]
    subprocess.call(cmd, cwd=path)
    subprocess.call(['make', '-j4'], cwd=path)


def fetch_cudd(
        ) -> None:
    """Retrieve, unpack, patch, and compile CUDD."""
    filename = CUDD_TARBALL
    fetch(CUDD_URL, CUDD_SHA256, filename)
    untar(filename)
    make_cudd()


def download_licenses(
        ) -> None:
    """Fetch licenses of dependencies.

    These licenses are included in the wheel of `dd`.
    The license files are placed in
    the directory `extern/`.
    """
    license_dir = 'extern'
    if not os.path.isdir(license_dir):
        os.mkdir(license_dir)
    join = _ft.partial(os.path.join, license_dir)
    # download GLIBC licenses
    glibc_license_file = join('GLIBC_COPYING.LIB')
    glibc_license_url = '''
        https://sourceware.org/git/
        ?p=glibc.git;a=blob_plain;f=COPYING.LIB;hb=HEAD
        '''
    _fetch_file(glibc_license_url, glibc_license_file)
    glibc_licenses_file = join('GLIBC_LICENSES')
    glibc_licenses_url = '''
        https://sourceware.org/git/
        ?p=glibc.git;a=blob_plain;f=LICENSES;hb=HEAD
        '''
    _fetch_file(glibc_licenses_url, glibc_licenses_file)
    # download CPython license
    py_license_file = join('PYTHON_LICENSE')
    numbers = sys.version_info[:2]
    python_version = '.'.join(map(str, numbers))
    py_license_url = f'''
        https://raw.githubusercontent.com/
        python/cpython/{python_version}/LICENSE
        '''
    _fetch_file(py_license_url, py_license_file)
    print('Downloaded license files.')


def _fetch_file(
        url:
            str,
        filename:
            str
        ) -> None:
    """Dump `url` to `filename`.

    Removes blankspace from `url`.
    """
    url = ''.join(url.split())
    response = urllib.request.urlopen(url)
    if response is None:
        raise urllib.error.URLError(
            'Error when attempting to open '
            f'the URL:  {url}')
    with response, open(filename, 'wb') as fd:
        fd.write(response.read())


if __name__ == '__main__':
    fetch_cudd()
