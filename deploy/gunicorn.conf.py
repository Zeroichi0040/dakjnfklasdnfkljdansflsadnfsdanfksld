"""One worker shares the default in-memory rate limiter. Use shared storage before scaling."""

import os

bind = "0.0.0.0:" + os.getenv("PORT", "8000")
workers = 1
threads = 4
timeout = 45
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = None  # Application logs use route patterns, so reset tokens stay out of logs.
errorlog = "-"
capture_output = True
