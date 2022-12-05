import typing

from opentelemetry.propagators.textmap import CarrierT
from opentelemetry.propagators.textmap import Getter


class DjangoStompGetter(Getter[CarrierT]):
    """Propagators class to get trace-parent header from a message from messaging broker"""

    def get(self, carrier: CarrierT, key: str) -> typing.Optional[typing.List[str]]:
        value = carrier.get(key, None)
        return [value] if value is not None else None

    def keys(self, carrier: CarrierT) -> typing.List[str]:
        return []
