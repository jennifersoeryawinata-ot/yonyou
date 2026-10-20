# telemetry.py
import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler   # ← correct import
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from configs.config import settings
# ── Configuration ─────────────────────────────────────────────────────────────

ALLOY_ENDPOINT  = settings.OTEL_EXPORTER_OTLP_ENDPOINT
SERVICE_NAME    = settings.OTEL_SERVICE_NAME
SERVICE_VERSION = settings.OTEL_SERVICE_VERSION

# Cloud Run injects these automatically at runtime
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "unknown-project")
K_SERVICE   = os.getenv("K_SERVICE", "unknown-service")     # Cloud Run service name
K_REVISION  = os.getenv("K_REVISION", "unknown-revision")   # Cloud Run revision


def build_resource() -> Resource:
    """Build an OTel Resource with Cloud Run metadata."""
    return Resource.create({
        "service.name":      SERVICE_NAME,
        "service.version":   SERVICE_VERSION,
        "cloud.provider":    "gcp",
        "cloud.platform":    "gcp_cloud_run",
        "cloud.project.id":  GCP_PROJECT,
        "faas.name":         K_SERVICE,
        "faas.version":      K_REVISION,
    })


def setup_traces(resource: Resource) -> None:
    exporter = OTLPSpanExporter(
        endpoint=f"{ALLOY_ENDPOINT}/v1/traces",
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def setup_metrics(resource: Resource) -> None:
    exporter = OTLPMetricExporter(
        endpoint=f"{ALLOY_ENDPOINT}/v1/metrics",
    )
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def setup_logs(resource: Resource) -> None:
    exporter = OTLPLogExporter(
        endpoint=f"{ALLOY_ENDPOINT}/v1/logs",
    )
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    set_logger_provider(provider)

    # Bridge Python's standard logging → OTel logs
    # LoggingHandler converts stdlib log records into OTel log records
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
    logging.getLogger().addHandler(handler)

    # Also inject trace_id/span_id into every log record automatically
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    LoggingInstrumentor().instrument(set_logging_format=True)


def setup_telemetry() -> None:
    """Initialize all OTel signals. Call once at app startup, before FastAPI()."""
    resource = build_resource()
    setup_traces(resource)
    setup_metrics(resource)
    setup_logs(resource)

# ambil trace id
def get_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        return format(span_context.trace_id, "032x")
    return "no-trace-id"