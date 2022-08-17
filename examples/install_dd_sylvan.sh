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
cd sylvan
autoreconf -fi
./configure
make
# update the environment variable `LD_LIBRARY_PATH`
export LD_LIBRARY_PATH=`pwd`/src/.libs:$LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH


# Fetch and install `dd`
pip install -r <(echo "dd --install-option='--sylvan'")
# confirm that `dd.sylvan` did get installed
cd tests/
python -c 'import dd.sylvan'
