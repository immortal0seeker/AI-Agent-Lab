from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    display_name: str
    supports_streaming: bool
    supports_tools: bool
    supports_json: bool
    input_price_per_1m: Decimal | None = None
    output_price_per_1m: Decimal | None = None
