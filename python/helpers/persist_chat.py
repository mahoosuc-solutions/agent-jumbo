import json
import os
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any

from agent import Agent, AgentConfig, AgentContext, AgentContextType
from initialize import initialize_agent
from python.helpers import files, history
from python.helpers.log import Log, LogItem

CHATS_FOLDER = "data/chats"
LOG_SIZE = 1000
CHAT_FILE_NAME = "chat.json"


def get_chat_folder_path(ctxid: str):
    """
    Get the folder path for any context (chat or task).

    Args:
        ctxid: The context ID

    Returns:
        The absolute path to the context folder
    """
    return files.get_abs_path(CHATS_FOLDER, ctxid)


def get_chat_msg_files_folder(ctxid: str):
    return files.get_abs_path(get_chat_folder_path(ctxid), "messages")


def save_tmp_chat(context: AgentContext):
    """Save context to the chats folder"""
    # Skip saving BACKGROUND contexts as they should be ephemeral
    if context.type == AgentContextType.BACKGROUND:
        return

    path = _get_chat_file_path(context.id)
    files.make_dirs(path)
    data = _serialize_context(context)
    js = _safe_json_serialize(data, ensure_ascii=False)
    files.write_file(path, js)

    # Integrate with agent journal (never fail on journal errors)
    try:
        from python.helpers import agent_journal

        project_name = getattr(getattr(context, "active_project", None), "name", None)
        agent_journal.get_or_create_session(context.id, project_name)
    except Exception:
        pass


def save_tmp_chats():
    """Save all contexts to the chats folder"""
    for _, context in AgentContext._contexts.items():
        # Skip BACKGROUND contexts as they should be ephemeral
        if context.type == AgentContextType.BACKGROUND:
            continue
        save_tmp_chat(context)


def _migrate_chats_tmp_to_data():
    """Migrate chats from tmp/chats to data/chats if they exist"""
    old_chats_folder = files.get_abs_path("tmp/chats")
    new_chats_folder = files.get_abs_path(CHATS_FOLDER)

    # Check if old folder exists and has subdirectories
    if not os.path.isdir(old_chats_folder):
        return

    try:
        subdirs = [d for d in os.listdir(old_chats_folder) if os.path.isdir(os.path.join(old_chats_folder, d))]
        if not subdirs:
            return

        # Ensure new folder exists
        os.makedirs(new_chats_folder, exist_ok=True)

        migrated = 0
        for subdir in subdirs:
            old_path = os.path.join(old_chats_folder, subdir)
            new_path = os.path.join(new_chats_folder, subdir)

            # Skip if already exists at destination
            if os.path.exists(new_path):
                continue

            # Move the directory
            try:
                files.move_file(old_path, new_path)
                migrated += 1
            except Exception as e:
                print(f"Failed to migrate chat {subdir}: {e}")

        if migrated > 0:
            print(f"Migrated {migrated} chat(s) from tmp/chats to data/chats")
    except Exception as e:
        print(f"Error during chat migration: {e}")


def load_tmp_chats():
    """Load all contexts from the chats folder"""
    _migrate_chats_tmp_to_data()
    _convert_v080_chats()
    folders = files.list_files(CHATS_FOLDER, "*")
    json_files = []
    for folder_name in folders:
        json_files.append(_get_chat_file_path(folder_name))

    ctxids = []
    for file in json_files:
        try:
            js = files.read_file(file)
            data = json.loads(js)
            ctx = _deserialize_context(data)
            ctxids.append(ctx.id)
        except Exception as e:
            print(f"Error loading chat {file}: {e}")
    return ctxids


def _get_chat_file_path(ctxid: str):
    return files.get_abs_path(CHATS_FOLDER, ctxid, CHAT_FILE_NAME)


def _convert_v080_chats():
    json_files = files.list_files(CHATS_FOLDER, "*.json")
    for file in json_files:
        path = files.get_abs_path(CHATS_FOLDER, file)
        name = file.rstrip(".json")
        new = _get_chat_file_path(name)
        files.move_file(path, new)


def load_json_chats(jsons: list[str]):
    """Load contexts from JSON strings"""
    ctxids = []
    for js in jsons:
        data = json.loads(js)
        if "id" in data:
            del data["id"]  # remove id to get new
        ctx = _deserialize_context(data)
        ctxids.append(ctx.id)
    return ctxids


def export_json_chat(context: AgentContext):
    """Export context as JSON string"""
    data = _serialize_context(context)
    js = _safe_json_serialize(data, ensure_ascii=False)
    return js


def remove_chat(ctxid):
    """Remove a chat or task context"""
    # Mark work session as completed before removing chat
    try:
        from python.helpers import agent_journal

        db = agent_journal._get_db()
        agent_journal._ensure_schema(db)
        row = db.fetch_one(
            "SELECT id FROM work_sessions WHERE context_id=? AND status='active' ORDER BY started_at DESC LIMIT 1",
            (ctxid,),
        )
        if row:
            agent_journal.end_session(row["id"], status="completed")
    except Exception:
        pass

    path = get_chat_folder_path(ctxid)
    files.delete_dir(path)


def remove_msg_files(ctxid):
    """Remove all message files for a chat or task context"""
    path = get_chat_msg_files_folder(ctxid)
    files.delete_dir(path)


def _serialize_context(context: AgentContext):
    # serialize agents
    agents = []
    agent = context.agent0
    while agent:
        agents.append(_serialize_agent(agent))
        agent = agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)

    data = {k: v for k, v in context.data.items() if not k.startswith("_")}
    output_data = {k: v for k, v in context.output_data.items() if not k.startswith("_")}

    return {
        "id": context.id,
        "name": context.name,
        "created_at": (context.created_at.isoformat() if context.created_at else datetime.fromtimestamp(0).isoformat()),
        "type": context.type.value,
        "last_message": (
            context.last_message.isoformat() if context.last_message else datetime.fromtimestamp(0).isoformat()
        ),
        "agents": agents,
        "streaming_agent": (context.streaming_agent.number if context.streaming_agent else 0),
        "log": _serialize_log(context.log),
        "data": data,
        "output_data": output_data,
    }


def _serialize_agent(agent: Agent):
    data = {k: v for k, v in agent.data.items() if not k.startswith("_")}

    history = agent.history.serialize()

    return {
        "number": agent.number,
        "data": data,
        "history": history,
    }


def _serialize_log(log: Log):
    return {
        "guid": log.guid,
        "logs": [item.output() for item in log.logs[-LOG_SIZE:]],  # serialize LogItem objects
        "progress": log.progress,
        "progress_no": log.progress_no,
    }


def _deserialize_context(data):
    config = initialize_agent()
    log = _deserialize_log(data.get("log", None))

    context = AgentContext(
        config=config,
        id=data.get("id", None),  # get new id
        name=data.get("name", None),
        created_at=(
            datetime.fromisoformat(
                # older chats may not have created_at - backcompat
                data.get("created_at", datetime.fromtimestamp(0).isoformat())
            )
        ),
        type=AgentContextType(data.get("type", AgentContextType.USER.value)),
        last_message=(datetime.fromisoformat(data.get("last_message", datetime.fromtimestamp(0).isoformat()))),
        log=log,
        paused=False,
        data=data.get("data", {}),
        output_data=data.get("output_data", {}),
        # agent0=agent0,
        # streaming_agent=straming_agent,
    )

    agents = data.get("agents", [])
    agent0 = _deserialize_agents(agents, config, context)
    streaming_agent = agent0
    while streaming_agent and streaming_agent.number != data.get("streaming_agent", 0):
        streaming_agent = streaming_agent.data.get(Agent.DATA_NAME_SUBORDINATE, None)

    context.agent0 = agent0
    context.streaming_agent = streaming_agent

    return context


def _deserialize_agents(agents: list[dict[str, Any]], config: AgentConfig, context: AgentContext) -> Agent:
    prev: Agent | None = None
    zero: Agent | None = None

    for ag in agents:
        current = Agent(
            number=ag["number"],
            config=config,
            context=context,
        )
        current.data = ag.get("data", {})
        current.history = history.deserialize_history(ag.get("history", ""), agent=current)
        if not zero:
            zero = current

        if prev:
            prev.set_data(Agent.DATA_NAME_SUBORDINATE, current)
            current.set_data(Agent.DATA_NAME_SUPERIOR, prev)
        prev = current

    return zero or Agent(0, config, context)


# def _deserialize_history(history: list[dict[str, Any]]):
#     result = []
#     for hist in history:
#         content = hist.get("content", "")
#         msg = (
#             HumanMessage(content=content)
#             if hist.get("type") == "human"
#             else AIMessage(content=content)
#         )
#         result.append(msg)
#     return result


def _deserialize_log(data: dict[str, Any]) -> "Log":
    log = Log()
    log.guid = data.get("guid", str(uuid.uuid4()))
    log.set_initial_progress()

    # Deserialize the list of LogItem objects
    i = 0
    for item_data in data.get("logs", []):
        log.logs.append(
            LogItem(
                log=log,  # restore the log reference
                no=i,  # item_data["no"],
                type=item_data["type"],
                heading=item_data.get("heading", ""),
                content=item_data.get("content", ""),
                kvps=OrderedDict(item_data["kvps"]) if item_data["kvps"] else None,
                temp=item_data.get("temp", False),
            )
        )
        log.updates.append(i)
        i += 1

    return log


def _safe_json_serialize(obj, **kwargs):
    def serializer(o):
        if isinstance(o, dict):
            return {k: v for k, v in o.items() if is_json_serializable(v)}
        elif isinstance(o, (list, tuple)):
            return [item for item in o if is_json_serializable(item)]
        elif is_json_serializable(o):
            return o
        else:
            return None  # Skip this property

    def is_json_serializable(item):
        try:
            json.dumps(item)
            return True
        except (TypeError, OverflowError):
            return False

    return json.dumps(obj, default=serializer, **kwargs)
