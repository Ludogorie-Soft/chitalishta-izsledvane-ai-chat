"""Tracing utilities for LangSmith integration."""

import os
from typing import Any, Optional

import structlog
from langchain_core.tracers.context import tracing_v2_enabled

try:
    from langsmith import Client
except ImportError:
    Client = None

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Try to import LangChainTracer
try:
    from langchain.callbacks.tracers import LangChainTracer
except ImportError:
    try:
        from langchain_core.tracers.langchain import LangChainTracer
    except ImportError:
        LangChainTracer = None  # type: ignore


def get_langsmith_tracer() -> Optional[Any]:
    """
    Get a configured LangSmith tracer if tracing is enabled.

    Returns:
        LangChainTracer instance or None if disabled or dependencies missing.
    """
    if not settings.langchain_tracing_v2:
        return None

    if not settings.langchain_api_key:
        logger.warning("LangSmith tracing enabled but API key not provided.")
        return None

    if LangChainTracer is None:
        logger.warning("LangChainTracer not available. Install langchain.")
        return None

    try:
        # Configure tracer with settings
        logger.info(f"Initializing LangSmith tracer for project: {settings.langchain_project} at {settings.langchain_endpoint}")
        
        # Create client explicitly to ensure settings are respected
        client = None
        if Client:
            try:
                client = Client(
                    api_url=settings.langchain_endpoint,
                    api_key=settings.langchain_api_key,
                )
                # Verify connection by checking/creating project
                if not client.has_project(settings.langchain_project):
                    logger.info(f"Project '{settings.langchain_project}' not found, creating it...")
                    client.create_project(settings.langchain_project)
                    logger.info(f"Project '{settings.langchain_project}' created successfully.")
                else:
                    logger.info(f"Project '{settings.langchain_project}' verified/exists.")
                    
            except Exception as e:
                logger.error(f"LangSmith connection test failed: {e}")
                # We don't return None here, we let the tracer try anyway, 
                # but this log is crucial for debugging.
        
        tracer = LangChainTracer(
            project_name=settings.langchain_project,
            client=client,
        )
        logger.info("LangSmith tracer initialized successfully")
        return tracer
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith tracer: {e}")
        return None


def setup_langsmith_env():
    """
    Set up LangSmith environment variables.
    
    We set these for the client to work, but we generally avoid setting
    LANGCHAIN_TRACING_V2=true globally to maintain granular control over
    which chains are traced (e.g. excluding SQL agent).
    """
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    
    if settings.langchain_endpoint:
        logger.info(f"Setting LangSmith endpoint to: {settings.langchain_endpoint}")
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        
    if settings.langchain_project:
        logger.info(f"Setting LangSmith project to: {settings.langchain_project}")
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        
    # We purposefully do NOT set LANGCHAIN_TRACING_V2 here.
    # We will manually add the tracer to callbacks where needed.
