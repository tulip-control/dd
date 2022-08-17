#!/usr/bin/env bash


# Prepare environment for building `dd`.


set -x
set -e
sudo apt install \
    graphviz
dot -V
pip install --upgrade \
    pip \
    setuptools
# note that installing from `requirements.txt`
# would also install packages that
# may be absent from where `dd` will be installed
pip install cython
#
# install `sylvan`
# download
curl -L \
https://github.com/utwente-fmt/sylvan/tarball/v1.0.0 \
-o sylvan.tar.gz
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
export LD_LIBRARY_PATH=`pwd`/src/.libs:$LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH
if [[ -z "${DEPLOY_ENV}" ]]; then
    # store values to use in later steps for
    # environment variables
    echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH" \
    >> $GITHUB_ENV
fi
popd
