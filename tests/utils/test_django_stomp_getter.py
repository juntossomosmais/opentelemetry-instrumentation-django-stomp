import pytest

from opentelemetry.propagators.textmap import CarrierT

from opentelemetry_instrumentation_django_stomp.utils.django_stomp_getter import DjangoStompGetter


class TestDjangoStompGetter:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Arrange
        self.fake_object_key = "fake_key"
        self.fake_object_value = "fake_value"
        self.fake_carrier: CarrierT = {self.fake_object_key: self.fake_object_value}
        self.django_stomp_getter = DjangoStompGetter()

    def test_should_return_value_in_list_if_value_exists_in_carrier(self):
        # Act
        getter_result = self.django_stomp_getter.get(self.fake_carrier, self.fake_object_key)

        # Assert
        assert type(getter_result) == list
        assert len(getter_result) == len(self.fake_carrier)
        assert getter_result[0] == self.fake_object_value

    def test_should_return_none_if_value_not_exists_in_carrier(self):
        # Act
        getter_result = self.django_stomp_getter.get(self.fake_carrier, "other_key")
        # Assert
        assert getter_result is None

    def test_should_return_empty_array_in_keys_method_call(self):
        # Act
        getter_result = self.django_stomp_getter.keys(self.fake_carrier)
        # Assert
        assert getter_result == []
