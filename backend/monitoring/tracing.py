# monitoring/tracing.py
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Span, Status, StatusCode

from settings import Settings

_tracer_provider: TracerProvider | None = None


def configure_tracing(app: FastAPI, settings: Settings) -> None:
    global _tracer_provider

    if not settings.monitoring.otlp.enabled:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.monitoring.otlp.service_name,
            "service.version": settings.version,
            "deployment.environment": settings.environment.value,
        }
    )

    sampler = ParentBased(TraceIdRatioBased(settings.monitoring.otlp.sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    exporter = OTLPSpanExporter(endpoint=settings.monitoring.otlp.endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    app.state.tracer_provider = provider


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


@contextmanager
def trace_span(name: str, **attributes: Any) -> Iterator[Span]:
    tracer = get_tracer("neuralcore")
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def shutdown_tracing() -> None:
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None