"""Semantic chunking helpers."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str


def _split_oversized_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split one long paragraph on sentence boundaries, then words if needed."""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
        if sentence.strip()
    ]
    if len(sentences) <= 1:
        words = paragraph.split()
        chunks: list[str] = []
        current_words: list[str] = []
        for word in words:
            candidate = " ".join(current_words + [word])
            if current_words and len(candidate) > max_chars:
                chunks.append(" ".join(current_words))
                current_words = [word]
                continue
            current_words.append(word)
        if current_words:
            chunks.append(" ".join(current_words))
        return chunks

    chunks: list[str] = []
    current_sentences: list[str] = []
    for sentence in sentences:
        candidate = " ".join(current_sentences + [sentence])
        if current_sentences and len(candidate) > max_chars:
            chunks.append(" ".join(current_sentences))
            current_sentences = [sentence]
            continue
        current_sentences.append(sentence)
    if current_sentences:
        chunks.append(" ".join(current_sentences))
    return chunks


def chunk_text(text: str, max_chars: int = 1200) -> list[TextChunk]:
    """Chunk text on paragraph boundaries while respecting a soft size target."""
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    normalized_paragraphs: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            normalized_paragraphs.extend(_split_oversized_paragraph(paragraph, max_chars))
        else:
            normalized_paragraphs.append(paragraph)
    chunks: list[TextChunk] = []
    current_parts: list[str] = []

    for paragraph in normalized_paragraphs:
        candidate_parts = current_parts + [paragraph]
        candidate_text = "\n\n".join(candidate_parts)
        if current_parts and len(candidate_text) > max_chars:
            chunks.append(
                TextChunk(chunk_index=len(chunks), text="\n\n".join(current_parts))
            )
            current_parts = [paragraph]
            continue
        current_parts = candidate_parts

    if current_parts:
        chunks.append(TextChunk(chunk_index=len(chunks), text="\n\n".join(current_parts)))

    return chunks
