all : test LDAhid.o

# How we create LDAhid.o
LDAhid.o : LDAhid.c LDAhid.h
	gcc -o LDAhid.o -c LDAhid.c

# The final output is one or more linked object files
test : test.c LDAhid.o LDAhid.h
#	gcc -o test -lm -lpthread -lusb test.c LDAhid.o /usr/lib/libhid.a
	gcc -o test -lm -lpthread -lusbl test.c LDAhid.o


clean :
	rm -f LDAhid.o
	rm -f test

