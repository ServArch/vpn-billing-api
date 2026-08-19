
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VpnConfigCreate(BaseModel):
    user_id: int
    config_name: str
    server_location: str = "germany"


class VpnConfigResponse(BaseModel):
    id: int
    user_id: int
    config_name: str
    uuid_key: str
    server_location: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
