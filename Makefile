# build, install, test, release `dd`


SHELL := bash
wheel_file := $(wildcard dist/*.whl)

.PHONY: cudd install test
.PHONY: clean clean_all clean_cudd wheel_deps


build_cudd: clean cudd install test

build_sylvan: clean wheel_deps
	-pip uninstall -y dd
	export DD_SYLVAN=1; \
	pip install . -vvv --use-pep517 --no-build-isolation
	pip install pytest
	make test

sdist_test: clean wheel_deps
	pip install -U build cython
	export DD_CUDD=1 DD_BUDDY=1; \
	python -m build --sdist --no-isolation
	pushd dist; \
	pip install dd*.tar.gz; \
	tar -zxf dd*.tar.gz && \
	popd
	pip install pytest
	make -C dist/dd*/ -f ../../Makefile test

sdist_test_cudd: clean wheel_deps
	pip install build cython ply
	export DD_CUDD=1 DD_BUDDY=1; \
	python -m build --sdist --no-isolation
	yes | pip uninstall cython ply
	pushd dist; \
	tar -zxf dd*.tar.gz; \
	pushd dd*/; \
	export DD_FETCH=1 DD_CUDD=1; \
	pip install . -vvv --use-pep517 --no-build-isolation && \
	popd && popd
	pip install pytest
	make -C dist/dd*/ -f ../../Makefile test

# use to create source distributions for PyPI
sdist: clean wheel_deps
	-rm dist/*.tar.gz
	pip install -U build cython
	export DD_CUDD=1 DD_BUDDY=1 DD_SYLVAN=1; \
	python -m build --sdist --no-isolation

wheel_deps:
	pip install --upgrade pip setuptools wheel

# use to create binary distributions for PyPI
wheel: clean wheel_deps
	-rm dist/*.whl
	-rm wheelhouse/*.whl
	export DD_CUDD=1 DD_CUDD_ZDD=1; \
	pip wheel . \
	    -vvv \
	    --wheel-dir dist \
	    --no-deps
	@echo "-------------"
	auditwheel show dist/*.whl
	@echo "-------------"
	auditwheel repair --plat manylinux_2_17_x86_64 dist/*.whl
	@echo "-------------"
	auditwheel show wheelhouse/*.whl

install: wheel_deps
	export DD_CUDD=1; \
	pip install . -vvv --use-pep517 --no-build-isolation

reinstall: uninstall wheel_deps
	export DD_CUDD=1 DD_CUDD_ZDD DD_SYLVAN; \
	pip install . -vvv --use-pep517 --no-build-isolation

reinstall_buddy: uninstall wheel_deps
	export DD_BUDDY=1; \
	pip install . -vvv --use-pep517 --no-build-isolation

reinstall_cudd: uninstall wheel_deps
	export DD_CUDD=1 DD_CUDD_ZDD=1; \
	pip install . -vvv --use-pep517 --no-build-isolation

reinstall_sylvan: uninstall wheel_deps
	export DD_SYLVAN=1; \
	pip install . -vvv --use-pep517 --no-build-isolation

uninstall:
	pip uninstall -y dd

test:
	set -x; \
	pushd tests; \
	python -X dev -m pytest -v --continue-on-collection-errors . && \
	popd
# `pytest -Werror` turns all warnings into errors
#     <https://docs.pytest.org/en/latest/how-to/capture-warnings.html>
# including pytest warnings about unraisable exceptions:
#     <https://docs.pytest.org/en/latest/how-to/failures.html
#         #warning-about-unraisable-exceptions-and-unhandled-thread-exceptions>
#     <https://docs.pytest.org/en/latest/reference/reference.html
#         #pytest.PytestUnraisableExceptionWarning>

test_abc:
	python -X dev tests/inspect_cython_signatures.py

test_examples:
	pushd examples/; \
	for script in `ls *.py`;  \
	do \
	    echo "Running: $$script"; \
	    python -X dev $$script; \
	done && \
	popd

show_deprecated:
	python -X dev -Wall -c "from dd import bdd"

typecheck:
	pytype \
	    -k \
	    -v 1 \
	    -j 'auto' \
	        dd/*.py \
	        setup.py \
	        install.py \
	        examples/*.py
	        # tests/*.py
	        # download.py

clean_type_cache:
	-rm -rf .pytype/

cudd:
	pushd cudd-*/; \
	make build XCFLAGS="\
	    -fPIC \
	    -mtune=native \
	    -DHAVE_IEEE_754 \
	    -DBSD \
	    -DSIZEOF_VOID_P=8 \
	    -DSIZEOF_LONG=8" && \
	popd

doc:
	grip --export doc.md index.html

download_licenses:
	python -c 'import download; \
	download.download_licenses()'

clean_all: clean_cudd clean

clean_cudd:
	pushd cudd-*/; make clean && popd

clean:
	-rm -rf build/ dist/ dd.egg-info/
	-rm dd/*.so
	-rm dd/buddy.c
	-rm dd/cudd.c
	-rm dd/cudd_zdd.c
	-rm dd/sylvan.c
	-rm *.pyc */*.pyc
	-rm -rf __pycache__ */__pycache__
	-rm -rf wheelhouse

rm_cudd:
	-rm -rf cudd*/ cudd*.tar.gz
