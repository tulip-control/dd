"""Retrieve and build dependencies of C extensions."""
import ctypes
import hashlib
import os
import subprocess
import sys
import tarfile
try:
    import urllib2
except ImportError:
    import urllib.request, urllib.error, urllib.parse
    urllib2 = urllib.request
try:
    from Cython.Build import cythonize
    pyx = '.pyx'
except ImportError:
    print('`import cython` failed')
    pyx = '.c'
from setuptools.extension import Extension


EXTENSIONS = ['cudd', 'buddy', 'sylvan']
# CUDD
CUDD_VERSION = '3.0.0'
CUDD_URL = (
    'ftp://vlsi.colorado.edu/'
    'pub/cudd-{v}.tar.gz').format(v=CUDD_VERSION)
CUDD_SHA256 = (
    'b8e966b4562c96a03e7fbea239729587'
    'd7b395d53cadcc39a7203b49cf7eeb69')
CC = 'gcc'
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
CUDD_PATH = os.path.join(
    FILE_PATH,
    'cudd-{v}'.format(v=CUDD_VERSION))
CUDD_DIRS = ['cudd', 'dddmp', 'epd', 'mtr', 'st', 'util']
CUDD_INCLUDE = ['.'] + CUDD_DIRS
CUDD_LINK = ['cudd/.libs', 'dddmp/.libs']
CUDD_LIB = ['cudd', 'dddmp']
CUDD_CFLAGS = [
    # '-arch x86_64',
    '-fPIC',
    '-DBSD',
    '-DHAVE_IEEE_754',
    '-mtune=native', '-pthread', '-fwrapv',
    '-fno-strict-aliasing',
    '-Wall', '-W', '-O3']
sizeof_long = ctypes.sizeof(ctypes.c_long)
sizeof_void_p = ctypes.sizeof(ctypes.c_void_p)
CUDD_CFLAGS.extend([
    '-DSIZEOF_LONG={long}'.format(long=sizeof_long),
    '-DSIZEOF_VOID_P={void}'.format(void=sizeof_void_p)])
# add -fPIC
XCFLAGS = (
    'XCFLAGS=-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD '
    '-DSIZEOF_VOID_P={void} -DSIZEOF_LONG={long}'.format(
        long=sizeof_long, void=sizeof_void_p))
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
    directives = dict()
    cudd_cflags = list(CUDD_CFLAGS)
    sylvan_cflags = list()
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
    extensions = dict(
        cudd=Extension(
            'dd.cudd',
            sources=['dd/cudd' + pyx],
            include_dirs=_join(cudd_include),
            library_dirs=_join(cudd_link),
            libraries=CUDD_LIB,
            extra_compile_args=cudd_cflags),
        buddy=Extension(
            'dd.buddy',
            sources=['dd/buddy' + pyx],
            libraries=['bdd']),
        sylvan=Extension(
            'dd.sylvan',
            sources=['dd/sylvan' + pyx],
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
                [v], compiler_directives=directives)
            ext_modules.append(c[0])
    else:
        ext_modules = list(extensions.values())
    return ext_modules


def _join(paths):
    return [os.path.join(*x) for x in paths]


def fetch(url, sha256, fname=None):
    print('++ download: {url}'.format(url=url))
    u = urllib2.urlopen(url)
    if fname is None:
        fname = url.split('/')[-1]
    with open(fname, 'wb') as f:
        f.write(u.read())
    with open(fname, 'rb') as f:
        s = f.read()
        h = hashlib.sha256(s)
        x = h.hexdigest()
        assert x == sha256, (x, sha256)
    print('-- done downloading.')
    return fname


def untar(fname):
    """Extract contents of tar file `fname`."""
    print('++ unpack: {f}'.format(f=fname))
    with tarfile.open(fname) as tar:
        tar.extractall()
    print('-- done unpacking.')


def make_cudd():
    """Compile CUDD."""
    path = CUDD_PATH
    cmd = ["./configure", "CFLAGS=-fPIC"]
    subprocess.call(cmd, cwd=path)
    subprocess.call(['make', '-j4'], cwd=path)


def fetch_cudd():
    """Retrieve, unpack, patch, and compile CUDD."""
    fname = fetch(CUDD_URL, CUDD_SHA256)
    untar(fname)
    make_cudd()


if __name__ == '__main__':
    fetch_cudd()
