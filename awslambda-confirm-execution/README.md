# About

This test creates a lambda and an HTTP Server

Each lambda invocation calls back to the web server with verrification that it managed to actually start executing.

These records are then compared against the results of all the invocations to make sure every lambda both executed and returned its results properly.

This test, as all tests, should be runnable in high concurrency.