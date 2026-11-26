"""
ClaimAugment AI - Middleware Layer
Implements Request ID injection, Latency Tracking, and Security Headers.
"""

import time
import uuid
import logging
from flask import request, g

logger = logging.getLogger("claimaugment.access")

def init_middleware(app):
    """
    Registers request lifecycle middleware with the Flask application instance.
    """

    @app.before_request
    def start_timer_and_correlation_id():
        """
        Runs BEFORE any controller handles the request.
        1. Captures or generates an X-Request-ID (UUID4).
        2. Records start timestamp in Flask's request context store (g).
        """
        # Accept client-provided X-Request-ID (e.g. from an API gateway) or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()

    @app.after_request
    def attach_headers_and_log(response):
        """
        Runs AFTER the controller returns a response.
        1. Injects X-Request-ID and X-Response-Time into outgoing HTTP headers.
        2. Logs the structured request summary.
        3. Appends production security headers.
        """
        # Calculate round-trip execution latency
        latency_ms = 0.0
        if hasattr(g, "start_time"):
            latency_ms = round((time.time() - g.start_time) * 1000, 2)

        request_id = getattr(g, "request_id", "unknown")

        # 1. Attach trace headers to the response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        # 2. Defense-in-depth security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Structured access log
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"status={response.status_code} latency={latency_ms}ms ip={request.remote_addr}"
        )

        return response