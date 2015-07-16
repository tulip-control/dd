build: clean cudd develop

develop:
	python setup.py develop

cudd:
	cd cudd-2.5.1; \
	make build XCFLAGS="-fPIC -mtune=native -DHAVE_IEEE_754 -DBSD -DSIZEOF_VOID_P=8 -DSIZEOF_LONG=8"

clean_all: clean_cudd clean

clean_cudd:
	cd cudd-2.5.1; make clean

rm_cudd:
	-rm -rf cudd*/ cudd*.tar.gz

clean:
	-rm -rf build/ dist/ dd.egg-info/ dd/*.so dd/*.c

