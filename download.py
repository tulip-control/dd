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
    from Cython.Compiler.Options import directive_defaults
    # directive_defaults['linetrace'] = True
    # directive_defaults['binding'] = True
except ImportError:
    pyx = '.c'
from setuptools.extension import Extension


CUDD_VERSION = '2.5.1'
CUDD_URL = (
    'ftp://vlsi.colorado.edu/'
    'pub/cudd-{v}.tar.gz').format(v=CUDD_VERSION)
CUDD_SHA256 = (
    '4b19c34328d8738a839b994c6b9395f3'
    '895ff981d2f3495ce62e7ba576ead88b')
CUDD_PATCH = (
    'https://raw.githubusercontent.com/LTLMoP/slugs'
    '/master/tools/CuddOSXFixes.patch')
CUDD_PATCH_SHA256 = (
    '8de3ceb2930efd2e16a5d90990be4586'
    '42b43dede3a96b2aa6cab7cc3ceb6e5d')
CC = 'gcc'
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
CUDD_PATH = os.path.join(
    FILE_PATH,
    'cudd-{v}'.format(v=CUDD_VERSION))
CUDD_INCLUDE = [
    [CUDD_PATH, 'include']]
CUDD_LINK = [
    [CUDD_PATH, 'cudd'],
    [CUDD_PATH, 'dddmp'],
    [CUDD_PATH, 'epd'],
    [CUDD_PATH, 'mtr'],
    [CUDD_PATH, 'st'],
    [CUDD_PATH, 'util']]
CUDD_LIB = ['cudd', 'dddmp', 'epd', 'mtr', 'st', 'util']
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
    '-DSIZEOF_VOID_P={void}'.format(void=sizeof_void_p),
    # '-DCYTHON_TRACE'
    ])
# add -fPIC
XCFLAGS = (
    'XCFLAGS=-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD '
    '-DSIZEOF_VOID_P={void} -DSIZEOF_LONG={long}'.format(
        long=sizeof_long, void=sizeof_void_p))


def extensions():
    os.environ['CC'] = CC
    extensions = dict(
        cudd=Extension(
            'dd.cudd',
            sources=['dd/cudd' + pyx],
            include_dirs=_join(CUDD_INCLUDE),
            library_dirs=_join(CUDD_LINK),
            libraries=CUDD_LIB,
            extra_compile_args=CUDD_CFLAGS),
        buddy=Extension(
            'dd.buddy',
            sources=['dd/buddy' + pyx],
            libraries=['bdd']))
    if pyx == '.pyx':
        for k, v in extensions.items():
            extensions[k] = cythonize(v)[0]
    return extensions


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
    print('++ unpack: {f}'.format(f=fname))
    with tarfile.open(fname) as tar:
        tar.extractall()
    print('-- done unpacking.')


def make_cudd():
    print('++ make CUDD')

    cwd = CUDD_PATH
    patch = 'osx.patch'
    fname = os.path.join(cwd, patch)
    fetch(CUDD_PATCH, CUDD_PATCH_SHA256, fname=fname)
    subprocess.call(['patch', '-p0', '-i', patch], cwd=cwd)
    subprocess.call(['make', 'build', XCFLAGS], cwd=cwd)
    print('-- done making CUDD.')


def fetch_cudd():
    """Retrieve, unpack, patch, and compile CUDD."""
    fname = fetch(CUDD_URL, CUDD_SHA256)
    untar(fname)
    make_cudd()


if __name__ == '__main__':
    fetch_cudd()
