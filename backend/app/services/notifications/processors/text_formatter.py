"""
Text Formatter Processor

Formats workshop result text for different notification channels.
"""

import re
from typing import Optional

from app.core.logging_config import get_logger
from app.services.notifications.context import NotificationContext

logger = get_logger(__name__)


class TextFormatterProcessor:
    """
    Formats text content for notifications.

    Supports multiple output formats:
    - plain: Plain text (strip markdown, HTML)
    - markdown: Markdown formatting (default)
    - html: HTML formatting
    """

    def __init__(
        self,
        output_format: str = "markdown",
        max_length: Optional[int] = None,
        add_header: bool = True,
        add_footer: bool = False,
    ):
        """
        Initialize text formatter.

        Args:
            output_format: Output format (plain, markdown, html)
            max_length: Maximum length in characters (None = unlimited)
            add_header: Whether to add title header
            add_footer: Whether to add attribution footer
        """
        self.output_format = output_format
        self.max_length = max_length
        self.add_header = add_header
        self.add_footer = add_footer

    async def process(self, context: NotificationContext) -> NotificationContext:
        """
        Format text content according to configuration.

        Args:
            context: Notification context

        Returns:
            Modified context with formatted_text set
        """
        try:
            text = context.result_text

            # Add header if requested
            if self.add_header:
                title = context.get_item_title()
                workshop_name = context.workshop.name
                text = self._add_header(text, title, workshop_name)

            # Format according to output format
            if self.output_format == "plain":
                text = self._to_plain(text)
            elif self.output_format == "html":
                text = self._to_html(text)
            # markdown is default, no transformation needed

            # Truncate if max_length specified
            if self.max_length and len(text) > self.max_length:
                text = text[: self.max_length - 3] + "..."

            # Add footer if requested
            if self.add_footer:
                text = self._add_footer(text)

            context.formatted_text = text
            context.mark_processed_by("text_formatter")

            logger.debug(f"Formatted text: {len(text)} chars, format={self.output_format}")

        except Exception as e:
            error_msg = f"Text formatting failed: {e}"
            logger.error(error_msg, exc_info=True)
            context.add_error(error_msg)
            # Fallback: use raw text
            context.formatted_text = context.result_text

        return context

    def _add_header(self, text: str, title: str, workshop_name: str) -> str:
        """Add title header to text."""
        if self.output_format == "markdown":
            return f"# {title}\n\n> 来自工坊: {workshop_name}\n\n{text}"
        elif self.output_format == "html":
            return f"<h1>{title}</h1><p><em>来自工坊: {workshop_name}</em></p>{text}"
        else:  # plain
            return f"{title}\n来自工坊: {workshop_name}\n\n{text}"

    def _add_footer(self, text: str) -> str:
        """Add attribution footer to text."""
        footer_text = "\n\n---\n由 MindEcho 自动生成"
        if self.output_format == "html":
            footer_text = "<hr><p><em>由 MindEcho 自动生成</em></p>"
        return text + footer_text

    def _to_plain(self, text: str) -> str:
        """Convert markdown/HTML to plain text."""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove markdown formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)  # Italic
        text = re.sub(r"`(.+?)`", r"\1", text)  # Code
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # Headers
        text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)  # Lists
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # Links

        return text.strip()

    def _to_html(self, text: str) -> str:
        """Convert markdown to HTML (basic conversion)."""
        # This is a simplified converter. For production, use `markdown` library
        html = text

        # Headers
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # Code
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # Links
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

        # Line breaks
        html = html.replace("\n\n", "</p><p>")
        html = f"<p>{html}</p>"

        return html
