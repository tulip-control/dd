import pip
from setuptools import setup


description = 'Library of decision diagrams and algorithms on them.'
README = 'README.md'
VERSION_FILE = 'dd/version.py'
MAJOR = 0
MINOR = 0
MICRO = 1
version = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
s = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n").format(version=version)


if __name__ == '__main__':
    pip.main(['install', 'ply == 3.4'])
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
    from dd import dddmp
    dddmp._rewrite_tables('dd/')
    setup(
        name='dd',
        version=version,
        description=description,
        long_description=open(README).read(),
        author='Ioannis Filippidis',
        author_email='jfilippidis@gmail.com',
        url='https://github.com/johnyf/dd',
        license='BSD',
        install_requires=['networkx >= 1.9.1', 'ply == 3.4'],
        extras_require={'dot': 'pydot', 'expr': 'tulip >= 1.2.dev'},
        tests_require=['nose'],
        packages=['dd'],
        package_dir={'dd': 'dd'},
        keywords=['bdd', 'binary decision diagram',
                  'decision diagram', 'networkx', 'boolean'])
