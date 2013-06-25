AUTOMAKE_OPTIONS = parallel-tests
AM_TESTS_ENVIRONMENT = MAKE_CHECK=True; export MAKE_CHECK;
TESTS = Test-stdouterr \
	Test-O \
	TestProto \
	Test-redirect \
	Test-Head \
	Test-c-partial \
	Test-Content-disposition \
	Test-Post \
	Test-Post2 \
	Test-Post3
XFAIL_TESTS = Test-Post \
	      Test-Post2 \
	      Test-Post3 \
	      Test-Put
LOG_COMPILER = ./runTest.py
