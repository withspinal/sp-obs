from abc import abstractmethod, ABCMeta
from typing import Any


class BaseProvider(metaclass=ABCMeta):
    def handle_event_stream(self, event_stream: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def parse_response_attributes(self, response_attributes: dict[str, Any]) -> dict[str, Any]:
        pass

    def parse_request_attributes(self, request_attributes: dict[str, Any]) -> dict[str, Any]:
        return request_attributes

    def parse_response_headers(self, _: dict[str, str]) -> dict[str, str]:
        """By default, no headers are parsed"""
        return {}
