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
BUDDY_INSTALL_PREFIX=`pwd`
BUDDY_ARCHIVE=buddy-2.4.tar.gz
BUDDY_URL=https://sourceforge.net/projects/buddy/\
files/buddy/BuDDy%202.4/buddy-2.4.tar.gz/download
curl -L $BUDDY_URL -o $BUDDY_ARCHIVE
tar -xzf $BUDDY_ARCHIVE
pushd buddy-*/
./configure \
    --prefix=$BUDDY_INSTALL_PREFIX
    # as described in
    # the README file of BuDDy
make
make install
    # by default installs to:
    # `/usr/local/include/` and
    # `/usr/local/lib/`
    #
    # The installation location can
    # be changed with
    # `./configure --prefix=/where/to/install`
export CFLAGS="-I$BUDDY_INSTALL_PREFIX/include"
export LDFLAGS="-L$BUDDY_INSTALL_PREFIX/lib"
export LD_LIBRARY_PATH=\
$BUDDY_INSTALL_PREFIX/lib:$LD_LIBRARY_PATH
echo $CFLAGS
echo $LDFLAGS
echo $LD_LIBRARY_PATH
popd


# Fetch and install `dd`
pip install cython
pip install -r <(echo "dd --install-option='--buddy'")
    # passes `-lbdd` to the C compiler
#
# fetch `dd` source
pip download \
    --no-deps dd \
    --no-binary dd
tar -xzf dd-*.tar.gz
# confirm that `dd.buddy` did get installed
pushd dd-*/tests/
python -c 'import dd.buddy'
popd
