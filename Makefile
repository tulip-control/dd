# build, install, test, release `dd`


SHELL := bash
wheel_file := $(wildcard dist/*.whl)
temp_file := _temp.txt

.PHONY: cudd install test
.PHONY: clean clean_all clean_cudd


build_cudd: clean cudd install test

build_sylvan: clean
	-pip uninstall -y dd
	python setup.py install --sylvan
	pip install pytest
	make test

sdist_test: clean
	python setup.py sdist --cudd --buddy
	cd dist; \
	pip install dd*.tar.gz; \
	tar -zxf dd*.tar.gz
	pip install pytest
	make -C dist/dd*/ -f ../../Makefile test

sdist_test_cudd: clean
	pip install cython ply
	python setup.py sdist --cudd --buddy
	yes | pip uninstall cython ply
	cd dist; \
	tar -zxf dd*.tar.gz; \
	cd dd*; \
	python setup.py install --fetch --cudd
	pip install pytest
	make -C dist/dd*/ -f ../../Makefile test

# use to create source distributions for PyPI
sdist: clean
	-rm dist/*.tar.gz
	python setup.py sdist --cudd --buddy --sylvan

# use to create binary distributions for PyPI
wheel: clean
	-rm dist/*.whl
	-rm wheelhouse/*.whl
	python setup.py bdist_wheel --cudd --cudd_zdd
	@echo "-------------"
	auditwheel show dist/*.whl
	@echo "-------------"
	auditwheel repair --plat manylinux_2_17_x86_64 dist/*.whl
	@echo "-------------"
	auditwheel show wheelhouse/*.whl

install:
	python setup.py install --cudd

reinstall: uninstall
	python setup.py install --cudd --cudd_zdd --sylvan

reinstall_buddy: uninstall
	echo ". --install-option='--buddy'" \
	    > $(temp_file)
	pip install -vvv -r $(temp_file)

reinstall_cudd: uninstall
	python setup.py install --cudd --cudd_zdd

reinstall_sylvan: uninstall
	echo ". --install-option='--sylvan'" \
	    > $(temp_file)
	pip install -vvv -r $(temp_file)

uninstall:
	pip uninstall -y dd

develop:
	python setup.py develop

test:
	set -x; \
	cd tests/; \
	python -X dev -m pytest -v --continue-on-collection-errors .
# `pytest -Werror` turns all warnings into errors
#     https://docs.pytest.org/en/latest/how-to/capture-warnings.html
# including pytest warnings about unraisable exceptions:
#     https://docs.pytest.org/en/latest/how-to/failures.html
#         #warning-about-unraisable-exceptions-and-unhandled-thread-exceptions
#     https://docs.pytest.org/en/latest/reference/reference.html
#         #pytest.PytestUnraisableExceptionWarning

test_abc:
	python -X dev tests/inspect_cython_signatures.py

run_examples:
	cd examples/; \
	for script in `ls *.py`;  \
	do \
	    echo "Running: $$script"; \
	    python -X dev $$script; \
	done;

show_deprecated:
	python -X dev -Wall -c "from dd import bdd"

cudd:
	cd cudd-*; \
	make build XCFLAGS="-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD -DSIZEOF_VOID_P=8 -DSIZEOF_LONG=8"

doc:
	grip --export doc.md index.html

download_licenses:
	mkdir -p extern
	curl -L "https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=COPYING.LIB;hb=HEAD" -o extern/GLIBC_COPYING.LIB
	curl -L "https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=LICENSES;hb=HEAD" -o extern/GLIBC_LICENSES
	curl -L "https://raw.githubusercontent.com/python/cpython/3.9/LICENSE" -o extern/PYTHON_LICENSE

clean_all: clean_cudd clean

clean_cudd:
	cd cudd-*; make clean

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
