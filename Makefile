# The script `rtests.py` below is an adaptation of:
# https://github.com/tulip-control/tulip-control/blob/master/run_tests.py

wheel_file := $(wildcard dist/*.whl)

.PHONY: cudd install test
.PHONY: clean clean_all clean_cudd


build_cudd: clean cudd install test

build_sylvan: clean
	-pip uninstall -y dd
	python setup.py install --sylvan
	rtests.py --rednose

sdist_test: clean
	python setup.py sdist --cudd --buddy
	cd dist; \
	pip install dd*.tar.gz; \
	tar -zxf dd*.tar.gz
	pip install nose rednose
	rtests.py --rednose

sdist_test_cudd: clean
	pip install cython ply
	python setup.py sdist --cudd --buddy
	yes | pip uninstall cython ply
	cd dist; \
	tar -zxf dd*.tar.gz; \
	cd dd*; \
	python setup.py install --fetch --cudd
	pip install nose rednose
	rtests.py --rednose

# use to create source distributions for PyPI
sdist: clean
	-rm dist/*.tar.gz
	python setup.py sdist --cudd --buddy --sylvan

# use to create binary distributions for PyPI
wheel: clean
	-rm dist/*.whl
	python setup.py bdist_wheel --cudd
	@echo "-------------"
	auditwheel show dist/*.whl
	@echo "-------------"
	auditwheel repair dist/*.whl
	@echo "-------------"
	auditwheel show dist/*.whl

install:
	python setup.py install --cudd

reinstall:
	-pip uninstall -y dd
	python setup.py install --cudd

uninstall:
	-pip uninstall -y dd

develop:
	python setup.py develop

test:
	rtests.py --rednose

cudd:
	cd cudd-*; \
	make build XCFLAGS="-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD -DSIZEOF_VOID_P=8 -DSIZEOF_LONG=8"

doc:
	grip --export doc.md index.html

clean_all: clean_cudd clean

clean_cudd:
	cd cudd-*; make clean

clean:
	-rm -rf build/ dist/ dd.egg-info/
	-rm dd/*.so
	-rm dd/buddy.c
	-rm dd/cudd.c
	-rm dd/sylvan.c
	-rm *.pyc */*.pyc
	-rm -rf __pycache__ */__pycache__
	-rm -rf wheelhouse

rm_cudd:
	-rm -rf cudd*/ cudd*.tar.gz
