"""
Markdown-to-HTML formatter for Telegram messages.

Telegram supports a limited set of HTML tags: <b>, <i>, <u>, <s>, <code>, <pre>, <a>.
This converter transforms common markdown patterns to Telegram-compatible HTML.
"""

import re


def format_for_telegram(text: str) -> str:
    """Convert markdown text to Telegram-compatible HTML.

    Processing order is critical to avoid conflicts:
    1. Escape HTML special chars
    2. Code blocks (```)
    3. Inline code (`)
    4. Triple asterisks (***bold italic***)
    5. Bold (**text** and __text__)
    6. List markers (* , - , • ) — BEFORE italic to prevent * conflicts
    7. Headers (# ## ###)
    8. Horizontal rules (--- on own line)
    9. Italic (*text* and _text_) — safe now that list * is gone
    10. Links [text](url)
    11. Clean whitespace
    """
    if not text:
        return ""

    # 1. Escape HTML special chars first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # 2. Code blocks (``` ... ```) — process before inline code
    text = re.sub(
        r"```(\w*)\n?(.*?)```",
        lambda m: f"<pre>{_unescape_html(m.group(2).strip())}</pre>",
        text,
        flags=re.DOTALL,
    )

    # 3. Inline code (` ... `)
    text = re.sub(
        r"`([^`]+)`",
        lambda m: f"<code>{_unescape_html(m.group(1))}</code>",
        text,
    )

    # 4. Triple asterisks (***bold italic***) — process before bold/italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)

    # 5. Bold (**text** or __text__)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Close unclosed bold markers at end of lines
    text = re.sub(r"\*\*(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"__(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # 6. Unordered list items — MUST be before italic to prevent * conflicts
    # Convert * and - list markers to • before italic processing
    text = re.sub(r"^(\s*)-\s+", r"\1• ", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)\*\s+", r"\1• ", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)•\s+", r"\1• ", text, flags=re.MULTILINE)

    # 7. Headers (# Header, ## Header, ### Header)
    text = re.sub(r"^###\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # 8. Horizontal rules (--- or *** on own line)
    text = re.sub(r"^(?:---|\*\*\*)$", "────────────────", text, flags=re.MULTILINE)

    # 9. Italic (*text* or _text_) — safe now that list * markers are converted
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
    # Close unclosed italic markers at end of lines
    text = re.sub(r"(?<!\w)\*(.+)$", r"<i>\1</i>", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\w)_(.+)$", r"<i>\1</i>", text, flags=re.MULTILINE)

    # 10. Ordered list items (1. item, 2. item)
    text = re.sub(r"^\s*(\d+)\.\s+", r"\1. ", text, flags=re.MULTILINE)

    # 11. Links [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{_unescape_html(m.group(2))}">{_unescape_html(m.group(1))}</a>',
        text,
    )

    # 12. Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _unescape_html(text: str) -> str:
    """Restore HTML entities inside code/pre blocks so they display correctly."""
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    return text


def sanitize_for_telegram(text: str) -> str:
    """Ensure text is safe for Telegram HTML parse mode.

    Uses counter-based tag balancing to properly close unclosed tags
    and remove excess closing tags.
    """
    supported = ["b", "i", "u", "s", "code", "pre", "a"]

    for tag in supported:
        open_count = len(re.findall(rf"<{tag}(?:\s[^>]*)?>", text))
        close_count = len(re.findall(rf"</{tag}>", text))

        # Close excess open tags
        for _ in range(open_count - close_count):
            text += f"</{tag}>"

        # Remove excess close tags (would break Telegram parsing)
        if close_count > open_count:
            excess = close_count - open_count
            # Remove the last excess closing tags
            pattern = rf"</{tag}>"
            matches = list(re.finditer(pattern, text))
            for m in reversed(matches[-excess:]):
                text = text[:m.start()] + text[m.end():]

    return text


def strip_markdown(text: str) -> str:
    """Remove all markdown formatting from text for plain-text fallback."""
    if not text:
        return ""

    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove triple asterisks
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    # Remove bold
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    # Remove italic
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove strikethrough
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^(?:---|\*\*\*)$", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    # Remove ordered list numbers
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
