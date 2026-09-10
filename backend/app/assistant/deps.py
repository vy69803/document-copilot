"""Runtime dependencies injected into the PydanticAI agent at each turn."""

from dataclasses import dataclass, field

from app.assistant.outputs import SourcePassage


@dataclass
class DocumentAgentDeps:
    """Everything the agent needs to process one chat turn.

    Populated by the orchestrator before the agent runs.
    The agent reads `retrieved_passages` to ground its answer.
    """

    user_id: str
    thread_id: str
    message_history: list[dict] = field(default_factory=list)
    retrieved_passages: list[SourcePassage] = field(default_factory=list)
    retriever: object | None = None
