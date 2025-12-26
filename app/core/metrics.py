"""Prometheus metrics for performance monitoring."""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

import psutil
import structlog
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    REGISTRY,
)

logger = structlog.get_logger(__name__)

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

# RAG metrics
rag_queries_total = Counter(
    "rag_queries_total",
    "Total number of RAG queries",
    ["status"],
)

rag_query_duration_seconds = Histogram(
    "rag_query_duration_seconds",
    "RAG query duration in seconds",
    ["status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

rag_retrieval_duration_seconds = Histogram(
    "rag_retrieval_duration_seconds",
    "RAG retrieval duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

rag_documents_retrieved = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved in RAG queries",
    buckets=(1, 5, 10, 20, 50, 100),
)

# SQL metrics
sql_queries_total = Counter(
    "sql_queries_total",
    "Total number of SQL queries",
    ["status"],
)

sql_query_duration_seconds = Histogram(
    "sql_query_duration_seconds",
    "SQL query duration in seconds",
    ["status"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

# LLM metrics
llm_calls_total = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["model", "provider", "task", "status"],
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM call duration in seconds",
    ["model", "provider", "task"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total number of LLM tokens used",
    ["model", "provider", "type"],  # type: input, output, total
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total number of errors",
    ["error_type", "endpoint"],
)

# System metrics
system_cpu_percent = Gauge(
    "system_cpu_percent",
    "System CPU usage percentage",
)

system_memory_bytes = Gauge(
    "system_memory_bytes",
    "System memory usage in bytes",
    ["type"],  # type: used, available, total
)

system_memory_percent = Gauge(
    "system_memory_percent",
    "System memory usage percentage",
)

# Database connection pool metrics
db_pool_size = Gauge(
    "db_pool_size",
    "Database connection pool size",
)

db_pool_checked_in = Gauge(
    "db_pool_checked_in",
    "Number of checked-in database connections",
)

db_pool_checked_out = Gauge(
    "db_pool_checked_out",
    "Number of checked-out database connections",
)

db_pool_overflow = Gauge(
    "db_pool_overflow",
    "Number of overflow database connections",
)


def track_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(
        method=method, endpoint=endpoint, status=status
    ).observe(duration)


def track_rag_query(status: str, duration: float, documents_retrieved: int = 0) -> None:
    """Track RAG query metrics."""
    rag_queries_total.labels(status=status).inc()
    rag_query_duration_seconds.labels(status=status).observe(duration)
    if documents_retrieved > 0:
        rag_documents_retrieved.observe(documents_retrieved)


def track_rag_retrieval(duration: float) -> None:
    """Track RAG retrieval operation metrics."""
    rag_retrieval_duration_seconds.observe(duration)


def track_sql_query(status: str, duration: float) -> None:
    """Track SQL query metrics."""
    sql_queries_total.labels(status=status).inc()
    sql_query_duration_seconds.labels(status=status).observe(duration)


def track_llm_call(
    model: str,
    provider: str,
    task: str,
    status: str,
    duration: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Track LLM call metrics."""
    llm_calls_total.labels(
        model=model, provider=provider, task=task, status=status
    ).inc()
    llm_call_duration_seconds.labels(
        model=model, provider=provider, task=task
    ).observe(duration)

    if input_tokens > 0:
        llm_tokens_total.labels(model=model, provider=provider, type="input").inc(
            input_tokens
        )
    if output_tokens > 0:
        llm_tokens_total.labels(model=model, provider=provider, type="output").inc(
            output_tokens
        )
    if input_tokens > 0 or output_tokens > 0:
        total_tokens = input_tokens + output_tokens
        llm_tokens_total.labels(model=model, provider=provider, type="total").inc(
            total_tokens
        )


def track_error(error_type: str, endpoint: str) -> None:
    """Track error metrics."""
    errors_total.labels(error_type=error_type, endpoint=endpoint).inc()


def update_system_metrics() -> None:
    """Update system resource metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_percent.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_bytes.labels(type="used").set(memory.used)
        system_memory_bytes.labels(type="available").set(memory.available)
        system_memory_bytes.labels(type="total").set(memory.total)
        system_memory_percent.set(memory.percent)
    except Exception as e:
        logger.warning("failed_to_update_system_metrics", error=str(e))


def update_db_pool_metrics(pool) -> None:
    """Update database connection pool metrics."""
    try:
        if pool is None:
            return

        # SQLAlchemy pool attributes
        db_pool_size.set(pool.size())
        db_pool_checked_in.set(pool.checkedin())
        db_pool_checked_out.set(pool.checkedout())
        db_pool_overflow.set(pool.overflow())
    except Exception as e:
        logger.debug("failed_to_update_db_pool_metrics", error=str(e))


def timing_decorator(
    metric_func: Callable,
    *metric_args,
    **metric_kwargs,
) -> Callable:
    """
    Decorator to time function execution and record metrics.

    Args:
        metric_func: Function to call with metrics (e.g., track_rag_query)
        *metric_args: Positional arguments to pass to metric_func
        **metric_kwargs: Keyword arguments to pass to metric_func (can include 'status' key)

    Example:
        @timing_decorator(track_rag_query, status="success")
        def my_rag_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                # Update status in kwargs if not already set
                call_kwargs = {**metric_kwargs, "status": status}
                metric_func(*metric_args, duration=duration, **call_kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                # Update status in kwargs if not already set
                call_kwargs = {**metric_kwargs, "status": status}
                metric_func(*metric_args, duration=duration, **call_kwargs)

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    # Update system metrics before generating
    update_system_metrics()

    # Update database pool metrics if engine is available
    try:
        from app.db.database import engine
        if engine and hasattr(engine, "pool"):
            update_db_pool_metrics(engine.pool)
    except Exception:
        # Ignore errors if database is not available
        pass

    return generate_latest(REGISTRY)

