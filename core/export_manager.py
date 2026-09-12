"""Conversation export manager for rootChat.

Supports exporting conversations to:
- Markdown (.md)
- Plain Text (.txt)
- Structured JSON (.json)
"""

import json
import re
from datetime import datetime
from PySide6.QtWidgets import QFileDialog, QMessageBox
from utils.logger import logger


def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be safely used as a filename."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', "_", name.strip())
    return name[:50] or "conversation"


def export_to_markdown(conversation: dict, messages: list) -> str:
    """Formats conversation and its messages as a clean Markdown document."""
    title = conversation.get("title", "Untitled Conversation")
    model = conversation.get("model", "Unknown Model")
    created_at = conversation.get("created_at", datetime.now().isoformat())
    
    lines = [
        f"# {title}",
        "",
        f"- **Model:** `{model}`",
        f"- **Date:** {created_at}",
        f"- **Total Messages:** {len(messages)}",
        "",
        "---",
        ""
    ]
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "").strip()
        
        if role == "user":
            lines.append("### 👤 User\n")
            lines.append(f"{content}\n")
        elif role == "assistant":
            lines.append("### 🤖 Assistant\n")
            lines.append(f"{content}\n")
        else:
            lines.append(f"### ⚙ System ({role})\n")
            lines.append(f"{content}\n")
            
        lines.append("---\n")
        
    return "\n".join(lines)


def export_to_txt(conversation: dict, messages: list) -> str:
    """Formats conversation and its messages as plain text."""
    title = conversation.get("title", "Untitled Conversation")
    model = conversation.get("model", "Unknown Model")
    created_at = conversation.get("created_at", datetime.now().isoformat())
    
    header = [
        "=" * 60,
        f"TITLE: {title}",
        f"MODEL: {model}",
        f"DATE:  {created_at}",
        "=" * 60,
        ""
    ]
    
    body = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "").strip()
        body.append(f"[{role}]")
        body.append(content)
        body.append("-" * 40)
        body.append("")
        
    return "\n".join(header + body)


def export_to_json(conversation: dict, messages: list) -> str:
    """Formats conversation and its messages as formatted JSON."""
    data = {
        "conversation": {
            "id": conversation.get("id"),
            "title": conversation.get("title"),
            "model": conversation.get("model"),
            "is_pinned": bool(conversation.get("is_pinned", 0)),
            "is_archived": bool(conversation.get("is_archived", 0)),
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at")
        },
        "messages": [
            {
                "id": m.get("id"),
                "role": m.get("role"),
                "content": m.get("content"),
                "created_at": m.get("created_at")
            }
            for m in messages
        ]
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def prompt_and_export(parent, conversation: dict, messages: list, export_format: str = "markdown") -> tuple[bool, str]:
    """
    Prompts user with a save file dialog and writes the formatted conversation to disk.
    
    export_format can be: 'markdown', 'txt', or 'json'.
    Returns (success: bool, filepath: str)
    """
    fmt = export_format.lower()
    title = conversation.get("title", "conversation")
    safe_title = sanitize_filename(title)
    
    if fmt in ("markdown", "md"):
        filter_str = "Markdown Files (*.md);;All Files (*)"
        default_name = f"{safe_title}.md"
        content = export_to_markdown(conversation, messages)
    elif fmt in ("txt", "text"):
        filter_str = "Text Files (*.txt);;All Files (*)"
        default_name = f"{safe_title}.txt"
        content = export_to_txt(conversation, messages)
    elif fmt == "json":
        filter_str = "JSON Files (*.json);;All Files (*)"
        default_name = f"{safe_title}.json"
        content = export_to_json(conversation, messages)
    else:
        logger.error("Unknown export format: %s", export_format)
        return False, ""

    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        f"Export Conversation as {fmt.upper()}",
        default_name,
        filter_str
    )

    if not file_path:
        return False, ""

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Successfully exported conversation %s to %s", conversation.get("id"), file_path)
        return True, file_path
    except Exception as e:
        logger.error("Failed to export conversation: %s", e)
        QMessageBox.critical(parent, "Export Failed", f"Failed to write file:\n{e}")
        return False, ""
