import logging

from opentelemetry import trace

from opentelemetry_instrumentation_django_stomp.utils.traced_thread_pool_executor import TracedThreadPoolExecutor
from tests.support.otel_helpers import TestBase

_logger = logging.getLogger(__name__)


class TestTracedThreadPoolExecutor(TestBase):
    @staticmethod
    def dummy_function(*args, **kwargs):
        """Fake function to run in submit on TracedThreadPoolExecutor"""
        tracer = trace.get_tracer_provider().get_tracer(__name__)
        with tracer.start_as_current_span("dummy_function", end_on_exit=True):
            _logger.info("dummy_function executed")

    def test_traced_pool_executor_propagate_span_to_thread(self):
        # Arrange
        traced_pool_executor = TracedThreadPoolExecutor(
            tracer=trace.get_tracer(__name__), thread_name_prefix="test_pool"
        )

        # Act
        tracer = trace.get_tracer_provider().get_tracer(__name__)
        with tracer.start_as_current_span("TRACED_THREAD_POOL_EXECUTOR", end_on_exit=True):
            traced_pool_executor.submit(self.dummy_function, {"simple": "parameter"})

        # Assert
        finished_spans = self.get_finished_spans()
        finished_thread_span = finished_spans.by_name("TRACED_THREAD_POOL_EXECUTOR")
        finished_function_span = finished_spans.by_name("dummy_function")
        assert finished_function_span.parent.trace_id == finished_thread_span.context.trace_id
        assert finished_function_span.parent.span_id == finished_thread_span.context.span_id
        assert len(finished_spans) == 2

    def test_traced_pool_executor_without_propagate_span_to_thread(self):
        # Arrange
        traced_pool_executor = TracedThreadPoolExecutor(
            tracer=trace.get_tracer(__name__), thread_name_prefix="test_pool"
        )

        # Act
        traced_pool_executor.submit(self.dummy_function, {"simple": "parameter"})

        # Assert
        finished_spans = self.get_finished_spans()
        assert len(finished_spans) == 1
        assert finished_spans.by_name("dummy_function")
