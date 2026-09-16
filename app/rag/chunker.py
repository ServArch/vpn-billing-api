import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MarkdownChunk:
    title: str
    breadcrumbs: list[str]
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    @property
    def contextualized_text(self) -> str:
        breadcrumb_prefix = " > ".join(self.breadcrumbs)
        return f"[{breadcrumb_prefix}]\n{self.content}".strip()


class HeaderAwareMarkdownChunker:
    HEADER_REGEX = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(self, max_chunk_chars: int = 900, overlap_chars: int = 150):
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def chunk_file(self, file_path: Path | str) -> list[MarkdownChunk]:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return self.chunk_text(text, source_name=path.name)

    def chunk_text(self, text: str, source_name: str = "") -> list[MarkdownChunk]:
        lines = text.splitlines()
        chunks: list[MarkdownChunk] = []

        header_stack: list[tuple[int, str]] = []
        current_paragraphs: list[str] = []
        chunk_counter = 0

        def flush_chunk():
            nonlocal chunk_counter, current_paragraphs
            if not current_paragraphs:
                return
            body = "\n\n".join(current_paragraphs).strip()
            if not body:
                return

            breadcrumbs = [title for _, title in header_stack]
            current_title = header_stack[-1][1] if header_stack else "General"

            chunk = MarkdownChunk(
                title=current_title,
                breadcrumbs=breadcrumbs,
                content=body,
                chunk_index=chunk_counter,
                metadata={"source": source_name, "depth": len(header_stack)},
            )
            chunks.append(chunk)
            chunk_counter += 1
            current_paragraphs = []

        for line in lines:
            header_match = self.HEADER_REGEX.match(line)
            if header_match:
                flush_chunk()
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                # simple stack update
                while header_stack and header_stack[-1][0] >= level:
                    header_stack.pop()
                header_stack.append((level, title))
            else:
                stripped = line.strip()
                if stripped:
                    current_paragraphs.append(stripped)

        flush_chunk()
        return chunks
