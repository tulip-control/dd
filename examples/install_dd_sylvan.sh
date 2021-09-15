#!/usr/bin/env bash
#
# Install `dd`, including
# the module `dd.sylvan`.
# (which is written in Cython).
#
# To run this script, enter in
# a command-line environment:
#
# ./install_dd_sylvan.sh


set -v
set -e
# check for Sylvan build dependencies
if ! command -v autoreconf &> /dev/null
then
    echo "apt install autoconf"
    exit
fi
if ! command -v libtoolize &> /dev/null
then
    echo "apt install libtool"
    exit
fi
# Fetch and install Sylvan
SYLVAN_ARCHIVE=sylvan.tar.gz
SYLVAN_URL=https://github.com/\
utwente-fmt/sylvan/tarball/v1.0.0
curl -L $SYLVAN_URL -o $SYLVAN_ARCHIVE
# checksum
echo "9877fe07a8cfe9889152e29624a4c5b283\
cb34672ec524ccb3edb313b3057fbf8ef45622a4\
9796fae17aa24e0baea5ccfa18f1bc5923e3c552\
45ab3e3c1927c8  sylvan.tar.gz" | shasum -a 512 -c -
# unpack
mkdir sylvan
tar xzf sylvan.tar.gz -C sylvan --strip=1
pushd sylvan
autoreconf -fi
./configure
make
# update the environment variable `LD_LIBRARY_PATH`
export CFLAGS="-I`pwd`/src"
export LDFLAGS="-L`pwd`/src/.libs"
export LD_LIBRARY_PATH=`pwd`/src/.libs:$LD_LIBRARY_PATH
echo $CFLAGS
echo $LDFLAGS
echo $LD_LIBRARY_PATH
popd


# Fetch and install `dd`
export DD_SYLVAN=1
pip install dd \
    -vvv \
    --use-pep517 \
    --no-build-isolation
# fetch `dd` source
pip download \
    --no-deps dd \
    --no-binary dd
tar -xzf dd-*.tar.gz
# confirm that `dd.sylvan` did get installed
pushd dd-*/tests/
python -c 'import dd.sylvan'
popd
