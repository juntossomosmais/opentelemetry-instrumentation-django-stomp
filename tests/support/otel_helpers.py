from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace import export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import format_span_id
from opentelemetry.trace import format_trace_id
from opentelemetry.util._once import Once

from opentelemetry_instrumentation_django_stomp import DjangoStompInstrumentor


def get_traceparent_from_span(span):
    """Helper function to get traceparent for propagator, used to create header on publish message"""
    trace_id_formatted = format_trace_id(span.context.trace_id)
    span_id_formatted = format_span_id(span.context.span_id)
    trace_flags = span.context.trace_flags
    return f"00-{trace_id_formatted}-{span_id_formatted}-{trace_flags:02x}"


class FinishedTestSpans(list):
    """Helper class to find finished spans in tests to make assertions"""

    def __init__(self, test, spans):
        super().__init__(spans)
        self.test = test

    def by_name(self, name):
        for span in self:
            if span.name == name:
                return span
        self.test.fail(f"Did not find span with name {name}")
        return None

    def by_attr(self, key, value):
        for span in self:
            if span.attributes.get(key) == value:
                return span
        self.test.fail(f"Did not find span with attrs {key}={value}")
        return None


class TestBase:
    """Base test class with setup_method and teardown_method for telemetry parameters"""

    tracer_provider = None
    memory_exporter = None
    consumer_hook = None
    publisher_hook = None

    def setup_class(self):
        result = self.create_tracer_provider()
        self.tracer_provider, self.memory_exporter = result
        trace.set_tracer_provider(self.tracer_provider)
        DjangoStompInstrumentor().instrument(publisher_hook=self.publisher_hook, consumer_hook=self.consumer_hook)

    def teardown_method(self):
        self.memory_exporter.clear()

    def teardown_class(self):
        self.reset_trace_globals()
        DjangoStompInstrumentor().uninstrument()

    def get_finished_spans(self):
        return FinishedTestSpans(self, self.memory_exporter.get_finished_spans())

    @staticmethod
    def reset_trace_globals() -> None:
        """WARNING: only use this for tests."""
        trace._TRACER_PROVIDER_SET_ONCE = Once()
        trace._TRACER_PROVIDER = None
        trace._PROXY_TRACER_PROVIDER = trace.ProxyTracerProvider()

    @staticmethod
    def create_tracer_provider(**kwargs):
        """Helper to create a configured tracer provider.
        Creates and configures a `TracerProvider` with a
        `SimpleSpanProcessor` and a `InMemorySpanExporter`.
        All the parameters passed are forwarded to the TracerProvider
        constructor.
        Returns:
            A list with the tracer provider in the first element and the
            in-memory span exporter in the second.
        """
        tracer_provider = TracerProvider(**kwargs)
        memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleSpanProcessor(memory_exporter)
        tracer_provider.add_span_processor(span_processor)

        return tracer_provider, memory_exporter
