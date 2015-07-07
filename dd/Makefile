CUDD=$$HOME/github/dd/cudd-2.5.1
CFLAGS="-I$(CUDD)/include/ -DSIZEOF_LONG=8 -DCUDD_COMPILER_OPTIONS_SET -arch x86_64 -Wall -W -DUSE_CUDD -mtune=native -DHAVE_IEEE_754 -DBSD -DSIZEOF_VOID_P=8 -pthread -fPIC -fwrapv -O0 -fno-strict-aliasing"
LDFLAGS="-L$(CUDD)/cudd -L$(CUDD)/util -L$(CUDD)/mtr -L$(CUDD)/st -L$(CUDD)/dddmp -L$(CUDD)/epd -lcudd -ldddmp -lmtr -lepd -lst -lutil"

# BuDDy library include
# CFLAGS="-I /opt/local/include"
# LDFLAGS="-L /opt/local/lib -lbdd"

cudd:
	cd ..;\
	CFLAGS=$(CFLAGS) \
	LDFLAGS=$(LDFLAGS) \
	python ./dd/_setup.py build_ext --inplace -g

clean:
	-rm *.so
