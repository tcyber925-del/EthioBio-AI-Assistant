from typing import Any, Generic, TypeVar

from src.schemas.conversation import ConversationRequest

GatewayInput = TypeVar("GatewayInput")
GatewayOutput = TypeVar("GatewayOutput")


class BaseVoiceAdapter(Generic[GatewayInput, GatewayOutput]):

    def build_request(self, gateway_input: GatewayInput) -> ConversationRequest:
        raise NotImplementedError

    def extract_response(self, response_data: Any) -> GatewayOutput:
        raise NotImplementedError
