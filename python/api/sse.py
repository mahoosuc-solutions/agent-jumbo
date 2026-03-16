"""Server-Sent Events endpoint for real-time chat updates."""

from __future__ import annotations

import json
import time

from flask import Request, Response, stream_with_context

from python.helpers.api import ApiHandler


class SSE(ApiHandler):
    """Stream chat log updates via Server-Sent Events."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # GET requests don't need CSRF

    async def process(self, input: dict, request: Request) -> Response:
        from agent import AgentContext

        context_id = request.args.get("context", "")
        last_version = int(request.args.get("log_version", "0"))

        def event_stream():
            version = last_version
            log_guid = ""
            heartbeat_interval = 15  # seconds
            last_heartbeat = time.time()
            max_duration = 300  # 5 minutes max, then client reconnects

            start_time = time.time()

            while time.time() - start_time < max_duration:
                try:
                    ctx = AgentContext.get(context_id) if context_id else AgentContext.first()
                    if not ctx:
                        yield f"data: {json.dumps({'error': 'no_context'})}\n\n"
                        time.sleep(2)
                        continue

                    current_guid = getattr(ctx.log, "guid", "")
                    if log_guid and current_guid != log_guid:
                        # Context reset
                        version = 0
                        yield f"event: reset\ndata: {json.dumps({'log_guid': current_guid})}\n\n"

                    log_guid = current_guid

                    # Get log data
                    logs = ctx.log.output(version)
                    log_version = ctx.log.version

                    if log_version != version:
                        payload = {
                            "logs": logs,
                            "log_version": log_version,
                            "log_guid": log_guid,
                            "log_progress": getattr(ctx.log, "progress", ""),
                            "log_progress_active": getattr(ctx.log, "progress_active", False),
                            "paused": getattr(ctx, "paused", False),
                            "contexts": [
                                {"id": c.id, "name": getattr(c, "name", c.id)} for c in AgentContext._contexts.values()
                            ],
                        }
                        yield f"data: {json.dumps(payload, default=str)}\n\n"
                        version = log_version
                    elif time.time() - last_heartbeat >= heartbeat_interval:
                        # Send heartbeat
                        yield ": heartbeat\n\n"
                        last_heartbeat = time.time()

                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

                time.sleep(1)  # Poll internal state every second

            # Send reconnect hint
            yield f"event: reconnect\ndata: {json.dumps({'version': version})}\n\n"

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
