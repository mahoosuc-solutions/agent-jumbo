from typing import Any

from python.helpers import settings
from python.helpers.api import ApiHandler, Request, Response
from python.helpers.validators import validate_settings_input


class SetSettings(ApiHandler):
    async def process(self, input: dict[Any, Any], request: Request) -> dict[Any, Any] | Response:
        validate_settings_input(input)
        set = settings.convert_in(input)
        set = settings.set_settings(set)
        return {"settings": set}
