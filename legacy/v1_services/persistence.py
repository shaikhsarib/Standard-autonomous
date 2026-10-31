import json
import os
from datetime import datetime
from typing import Optional
from core.schemas import ConversationContext, LeadOutput

STORAGE_DIR = "storage"
SESSIONS_DIR = os.path.join(STORAGE_DIR, "sessions")
LEADS_DIR = os.path.join(STORAGE_DIR, "leads")

class PersistenceError(Exception):
    """Custom exception for persistence layer operations."""
    pass

def _ensure_directories() -> None:
    """Ensures that the storage directory structure exists."""
    try:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        os.makedirs(LEADS_DIR, exist_ok=True)
    except OSError as e:
        raise PersistenceError(f"Failed to create storage directories: {e}")

def save_conversation_context(context: ConversationContext) -> None:
    """
    Saves the absolute state of a conversation context to disk.

    Args:
        context: The ConversationContext object to save.
    Raises:
        PersistenceError: If there is an issue writing to disk.
    """
    _ensure_directories()
    file_path = os.path.join(SESSIONS_DIR, f"{context.session_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(context.model_dump_json())
    except (OSError, TypeError) as e:
        raise PersistenceError(f"Failed to save session {context.session_id}: {e}")

def load_conversation_context(session_id: str) -> Optional[ConversationContext]:
    """
    Loads a conversation context from disk by session ID.

    Args:
        session_id: The unique identifier for the session.
    Returns:
        The ConversationContext object if found, otherwise None.
    Raises:
        PersistenceError: If there is an issue reading from disk.
    """
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ConversationContext.model_validate_json(f.read())
    except (OSError, json.JSONDecodeError, ValueError) as e:
        raise PersistenceError(f"Failed to load session {session_id}: {e}")

def save_lead_output(lead: LeadOutput) -> None:
    """
    Saves extracted lead data to disk.

    Args:
        lead: The LeadOutput object to save.
    Raises:
        PersistenceError: If there is an issue writing to disk.
    """
    _ensure_directories()
    file_path = os.path.join(LEADS_DIR, f"{lead.session_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lead.model_dump_json())
    except (OSError, TypeError) as e:
        raise PersistenceError(f"Failed to save lead for session {lead.session_id}: {e}")