"""Initialize OpenTelemetry SDK and OpenLLMetry auto-instrumentation."""

import os

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from src.config import settings

logger = structlog.get_logger()


def init_otel() -> None:
    """Initialize OpenTelemetry tracing.

    Call once at application startup. Configures the TracerProvider with
    OTLP exporter (or no-op if endpoint is not set).
    """
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "1.1.0",
    })
    provider = TracerProvider(resource=resource)

    if settings.otel_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
        processor = (
            SimpleSpanProcessor(exporter)
            if settings.debug
            else BatchSpanProcessor(exporter)
        )
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def init_openllmetry() -> None:
    """Auto-instrument provider SDK calls via OpenLLMetry.

    Falls back silently if OpenLLMetry is not installed or configured.
    """
    if not os.environ.get("TRACELOOP_API_KEY"):
        logger.info("traceloop_skipped_no_api_key")
        return
    try:
        from traceloop.sdk import Traceloop

        Traceloop.init(
            app_name=settings.otel_service_name,
        )
    except Exception:
        logger.exception("traceloop_init_failed")
