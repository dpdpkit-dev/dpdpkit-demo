import os

# The site tests make many requests from one client; the rate limit has its own tests in test_ops.py.
os.environ.setdefault("DEMO_RATE_READ", "0")
os.environ.setdefault("DEMO_RATE_WRITE", "0")
