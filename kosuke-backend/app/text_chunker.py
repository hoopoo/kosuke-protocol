"""Text chunking utilities for fragment ingestion."""


def chunk_text(
    text: str,
    chunk_size: int = 300,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks suitable for fragment storage.

    Uses sentence-aware splitting to avoid breaking mid-sentence.
    """
    if not text.strip():
        return []

    # Split into sentences first
    sentences = _split_sentences(text)

    if not sentences:
        return []

    # If the entire text is short enough, return as single fragment
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_length = len(sentence)

        # If a single sentence exceeds chunk_size, add it as its own chunk
        if sentence_length > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep overlap
                overlap_text = " ".join(current_chunk)
                if len(overlap_text) > chunk_overlap:
                    current_chunk = [overlap_text[-chunk_overlap:]]
                    current_length = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_length = 0
            chunks.append(sentence)
            continue

        if current_length + sentence_length + 1 > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Create overlap by keeping some trailing content
            overlap_text = " ".join(current_chunk)
            if len(overlap_text) > chunk_overlap:
                current_chunk = [overlap_text[-chunk_overlap:]]
                current_length = len(current_chunk[0])
            else:
                current_chunk = []
                current_length = 0

        current_chunk.append(sentence)
        current_length += sentence_length + 1

    # Add remaining content
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return [c.strip() for c in chunks if c.strip()]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple heuristics."""
    import re

    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Also split on double newlines (paragraph breaks)
    result: list[str] = []
    for sentence in sentences:
        parts = sentence.split("\n\n")
        result.extend(parts)

    return [s.strip() for s in result if s.strip()]
