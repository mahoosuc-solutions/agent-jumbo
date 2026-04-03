import json

from flask import Response as FlaskResponse

from python.helpers.api import ApiHandler, Input, Request, Response
from python.helpers.work_mode.manager import WorkModeManager
from python.helpers.work_mode.types import WorkMode


class WorkModeSetHandler(ApiHandler):
    route_name = "work_mode_set"

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: Input, request: Request) -> dict | Response:
        raw_mode = input.get("mode", "")
        try:
            new_mode = WorkMode(raw_mode)
        except ValueError:
            return FlaskResponse(
                json.dumps({"error": f"invalid mode: {raw_mode!r}. Must be local, selective, or cloud"}),
                status=400,
                mimetype="application/json",
            )

        mgr = WorkModeManager.get_instance()
        mgr.request_switch(new_mode)

        return {"mode": mgr.get_mode().value, "ok": True}
