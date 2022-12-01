# Opentelemetry auto instrumentation for django-stomp

[//]: # ([![Build Status]&#40;https://dev.azure.com/juntos-somos-mais-loyalty/python/_apis/build/status/juntossomosmais.opentelemetry-instrumentation-django-stomp?branchName=main&#41;]&#40;https://dev.azure.com/juntos-somos-mais-loyalty/python/_build/latest?definitionId=272&branchName=main&#41;)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=juntossomosmais_opentelemetry-instrumentation-django-stomp&metric=sqale_rating&token=80cebbac184a793f8d0be7a3bbe9792f47a6ef23)](https://sonarcloud.io/summary/new_code?id=juntossomosmais_opentelemetry-instrumentation-django-stomp)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=juntossomosmais_opentelemetry-instrumentation-django-stomp&metric=coverage&token=80cebbac184a793f8d0be7a3bbe9792f47a6ef23)](https://sonarcloud.io/summary/new_code?id=juntossomosmais_opentelemetry-instrumentation-django-stomp)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=juntossomosmais_opentelemetry-instrumentation-django-stomp&metric=alert_status&token=80cebbac184a793f8d0be7a3bbe9792f47a6ef23)](https://sonarcloud.io/summary/new_code?id=juntossomosmais_opentelemetry-instrumentation-django-stomp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PyPI version](https://badge.fury.io/py/opentelemetry-instrumentation-django-stomp.svg)](https://badge.fury.io/py/opentelemetry-instrumentation-django-stomp)
[![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/juntossomosmais/opentelemetry-instrumentation-django-stomp/blob/main/LICENSE)

This library will help you to use opentelemetry traces and metrics on [Django STOMP](https://github.com/juntossomosmais/django-stomp) usage library.

![Django stomp instrumentation](docs/example.gif?raw=true)


####  Installation
pip install `opentelemetry-instrumentation-django-stomp`

#### How to use ?

You can use the `DjangoStompInstrumentor().instrument()` for example in `manage.py` file.


```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import typing

from opentelemetry_instrumentation_django_stomp import DjangoStompInstrumentor

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.trace.span import Span


def publisher_hook(span: Span, body: typing.Dict, headers: typing.Dict):
    # Custom code in your project here we can see span attributes and make custom logic with then.
    pass


def consumer_hook(span: Span, body: typing.Dict, headers: typing.Dict):
    # Custom code in your project here we can see span attributes and make custom logic with then.
    pass


provider = TracerProvider()
trace.set_tracer_provider(provider)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
    DjangoStompInstrumentor().instrument(
        trace_provider=trace,
        publisher_hook=publisher_hook,
        consumer_hook=consumer_hook,
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

The code above will create telemetry wrappers inside django-stomp code and creates automatic spans with broker data.

The `DjangoStompInstrumentor` can receive three optional parameters:
- **trace_provider**: The tracer provider to use in open-telemetry spans.
- **publisher_hook**: The callable function on publisher action to call before the original function call, use this to override, enrich the span or get span information in the main project.
- **consumer_hook**: The callable function on consumer action to call before the original function call, use this to override, enrich the span or get span information in the main project.

:warning: The hook function will not raise an exception when an error occurs inside hook function, only a warning log is generated

#### PUBLISHER example

With the django-stomp, we can publish a message to a broker using `publisher.send` and the instrumentator
can include a span with telemetry data in this function utilization.

```python
    from uuid import uuid4
    from django_stomp.builder import build_publisher
    publisher = build_publisher(f"publisher-unique-name-{uuid4()}")
    publisher.send(
        queue='/queue/a-destination',
        body={"a": "random","body": "message"},
    )
```

The publisher span had "PUBLISHER" name.

![publisher example](docs/publisher_example.png?raw=true)

#### CONSUMER example
With the django-stomp, we create a simple consumer using pubsub command and the instrumentator
can include a span with telemetry data in this function utilization.

```bash
   python manage.py pubsub QUEUE_NAME callback_function_to_consume_message
```

Consumer spans can generate up to three types:

- CONSUMER
![consumer example](docs/consumer_example.png?raw=true)
- ACK
![ack example](docs/ack_example.png?raw=true)
- NACK
![nack example](docs/nack_example.png?raw=true)

#### Supress django-stomp traces and metrics
When the flag `OTEL_PYTHON_DJANGO_STOMP_INSTRUMENT` has `False` value traces and metrics will not be generated.
Use this to supress the django-stomp instrumentation.

#### HOW TO CONTRIBUTE ?
Look the [contributing](./CONTRIBUTING.md) specs
