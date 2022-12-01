"""
This library supports the `django-stomp` library, it can be enabled by
using ``DjangoStompInstrumentor``.

*****************************************
USAGE
-----
In project manage.py you can include the example code below

.. code-block:: python
    from opentelemetry_instrumentation_django_stomp import DjangoStompInstrumentor

    def publisher_hook(span: Span, body: Dict, headers: Dict):
        # Custom code
        pass

    def consumer_hook(span: Span, body: Dict, headers: Dict):
        # Custom code
        pass

    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    DjangoStompInstrumentor().instrument(
        trace_provider=trace,
        publisher_hook=publisher_hook,
        consumer_hook=consumer_hook,
    )

*****************************************
PUBLISHER
-----
With the django-stomp we can publish a message to broker using `publisher.send` and the instrumentor
can include a span with telemetry data in this function utilization.

.. code-block:: python
   publisher = build_publisher(f"publisher-unique-name-{uuid4()}")
    publisher.send(
        queue=DESTINATION,
        body={"a": "random","body": "message},
    )

*****************************************
CONSUMER
-----
With the django-stomp we create a simple consumer using pubsub command and the instrumentor
can include a span with telemetry data in this function utilization.

.. code-block:: python
   python manage.py pubsub QUEUE_NAME callback_function_to_consume_message
"""
import threading
import typing

from django.conf import settings
from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import TracerProvider

from .instrumentors.consumer_instrument import ConsumerInstrument
from .instrumentors.publisher_instrument import PublisherInstrument
from .package import _instruments
from .utils.shared_types import CallbackHookT
from .version import __version__

_CTX_KEY = "__otel_django_stomp_span"

local_threading = threading.local()


class DjangoStompInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> typing.Collection[str]:
        """
        Function to check compatibility with dependencies package(django-stomp)
        """
        return _instruments

    def _uninstrument(self, **kwargs):
        """
        Function to unwrap publisher and consumer functions from django-stomp
        """
        if hasattr(self, "__opentelemetry_tracer_provider"):
            delattr(self, "__opentelemetry_tracer_provider")
        ConsumerInstrument().uninstrument()
        PublisherInstrument().uninstrument()

    def _instrument(self, **kwargs) -> None:
        """
        Instrument function to initialize wrappers in publisher and consumer functions from django-stomp.

        Args:
            kwargs (typing.Dict[str, typing.Any]):
                trace_provider (Optional[TracerProvider]): The tracer provider to use in open-telemetry spans.
                publisher_hook (CallbackHookT): The callable function to call before original function call, use
                this to override or enrich the span created in main project.
                consumer_hook (CallbackHookT): The callable function to call before original function call, use
                this to override or enrich the span created in main project.

        Returns:
        """
        instrument_django_stomp = getattr(settings, "OTEL_PYTHON_DJANGO_STOMP_INSTRUMENT", True)
        if not instrument_django_stomp:
            return None

        tracer_provider: typing.Optional[TracerProvider] = kwargs.get("tracer_provider", None)
        publisher_hook: CallbackHookT = kwargs.get("publisher_hook", None)
        consumer_hook: CallbackHookT = kwargs.get("consumer_hook", None)

        self.__setattr__("__opentelemetry_tracer_provider", tracer_provider)
        tracer = trace.get_tracer(__name__, __version__, tracer_provider)

        ConsumerInstrument().instrument(tracer=tracer, callback_hook=consumer_hook)
        PublisherInstrument().instrument(tracer=tracer, callback_hook=publisher_hook)
