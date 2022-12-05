import typing

from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context as otel_context
from opentelemetry.sdk.trace import Tracer


def with_otel_context(context: otel_context.Context, fn: typing.Callable):
    otel_context.attach(context)
    return fn()


class TracedThreadPoolExecutor(ThreadPoolExecutor):
    """Implementation of :class:`ThreadPoolExecutor` that will pass context into sub tasks."""

    def __init__(self, tracer: Tracer, *args, **kwargs):
        self.tracer = tracer
        super().__init__(*args, **kwargs)

    def submit(self, fn, *args, **kwargs):
        """Submit a new task to the thread pool."""
        context = otel_context.get_current()
        if context:
            return super().submit(
                lambda: with_otel_context(context, lambda: fn(*args, **kwargs)),
            )
        else:
            return super().submit(lambda: fn(*args, **kwargs))
