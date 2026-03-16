import json
import threading
from abc import abstractmethod
from typing import Any, TypedDict, Union

from flask import Flask, Request, Response, send_file, session

from agent import AgentContext
from initialize import initialize_agent
from python.helpers.errors import format_error
from python.helpers.print_style import PrintStyle

Input = dict
Output = Union[dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app: Flask, thread_lock: threading.Lock):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        from python.helpers import login

        return cls.requires_auth() and login.is_login_required()

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output:
        pass

    async def handle_request(self, request: Request) -> Response:
        try:
            # input data from request based on type
            input_data: Input = {}
            if request.is_json:
                try:
                    if request.data:  # Check if there's any data
                        input_data = request.get_json()
                    # If empty or not valid JSON, use empty dict
                except Exception as e:
                    # Just log the error and continue with empty input
                    PrintStyle().print(f"Error parsing JSON: {e!s}")
                    input_data = {}
            else:
                # input_data = {"data": request.get_data(as_text=True)}
                input_data = {}

            # process via handler
            output = await self.process(input_data, request)

            # return output based on type
            if isinstance(output, Response):
                return output
            else:
                import uuid as _uuid

                request_id = _uuid.uuid4().hex[:12]
                response_json = json.dumps(output)
                resp = Response(response=response_json, status=200, mimetype="application/json")
                resp.headers["X-Request-ID"] = request_id
                return resp

            # return exceptions with 500
        except Exception as e:
            import uuid as _uuid

            request_id = _uuid.uuid4().hex[:12]
            error = format_error(e)
            PrintStyle.error(f"API error [{request_id}]: {error}")
            response = Response(
                response=json.dumps({"error": "Internal server error", "request_id": request_id}),
                status=500,
                mimetype="application/json",
            )
            response.headers["X-Request-ID"] = request_id
            return response

    # get context to run agent zero in
    def use_context(self, ctxid: str, create_if_not_exists: bool = True):
        with self.thread_lock:
            if not ctxid:
                first = AgentContext.first()
                if first:
                    AgentContext.use(first.id)
                    return first
                context = AgentContext(config=initialize_agent(), set_current=True)
                return context
            got = AgentContext.use(ctxid)
            if got:
                return got
            if create_if_not_exists:
                context = AgentContext(config=initialize_agent(), id=ctxid, set_current=True)
                return context
            else:
                raise Exception(f"Context {ctxid} not found")
