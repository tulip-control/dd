#!/usr/bin/env bash
#
# Install `dd`, including the module
# `dd.buddy`, which is written in Cython.
#
# To run this script, enter in
# a command-line environment:
#
# ./install_dd_buddy.sh


set -v
set -e
# Fetch and build BuDDy
BUDDY_ARCHIVE=buddy-2.4.tar.gz
BUDDY_URL=https://sourceforge.net/projects/buddy/\
files/buddy/BuDDy%202.4/buddy-2.4.tar.gz/download
curl -L $BUDDY_URL -o $BUDDY_ARCHIVE
tar -xzf $BUDDY_ARCHIVE
pushd buddy-*/
./configure
    # as described in
    # the README file of BuDDy
make
make install
    # installs to:
    # `/usr/local/include/` and
    # `/usr/local/lib/`
    #
    # The installation location can
    # be changed with
    # `./configure --prefix=/where/to/install`
popd


# Fetch and install `dd`
pip install -r <(echo "dd --install-option='--buddy'")
    # passes `-lbdd` to the C compiler
#
# fetch `dd` source
pip download \
    --no-deps dd \
    --no-binary dd
tar -xzf dd-*.tar.gz
# confirm that `dd.buddy` did get installed
cd dd-*/tests/
python -c 'import dd.buddy'
