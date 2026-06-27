"""Optional OpenTelemetry export hooks."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_configured = False


def configure_otel_if_enabled() -> dict[str, Any]:
    """Configure OTLP export when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    global _configured
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return {"enabled": False, "reason": "OTEL_EXPORTER_OTLP_ENDPOINT not set"}

    if _configured:
        return {"enabled": True, "endpoint": endpoint, "status": "already_configured"}

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OTEL export requested but opentelemetry packages are not installed "
            "(install opentelemetry-sdk and opentelemetry-exporter-otlp-proto-http)"
        )
        return {"enabled": False, "reason": "opentelemetry packages missing"}

    service_name = os.environ.get("OTEL_SERVICE_NAME", "engine")
    resource = Resource.create({"service.name": service_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint))
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    _configured = True
    logger.info("OpenTelemetry export enabled for %s", endpoint)
    return {"enabled": True, "endpoint": endpoint, "service_name": service_name}
