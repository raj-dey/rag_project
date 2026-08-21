import uuid
from typing import List, Dict, Any


class RecursiveCharacterTextSplitter:
    """
    Robust character-based text splitter with recursive separator hierarchy.
    """
    def __init__(self, chunk_size: int = 750, chunk_overlap: int = 100, separators: List[str] = None, keep_separator: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " ", ""]
        self.keep_separator = keep_separator

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        final_chunks = []
        separator = self.separators[-1]
        for s in self.separators:
            if s == "":
                separator = s
                break
            if s in text:
                separator = s
                break

        splits = text.split(separator) if separator != "" else list(text)

        current_chunk = []
        current_length = 0

        for split in splits:
            item = split if (separator == "" or not self.keep_separator) else split + separator
            item_len = len(item)

            if current_length + item_len > self.chunk_size and current_chunk:
                joined = "".join(current_chunk).strip()
                if joined:
                    final_chunks.append(joined)

                overlap_len = 0
                overlap_items = []
                for prev in reversed(current_chunk):
                    if overlap_len + len(prev) <= self.chunk_overlap:
                        overlap_items.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current_chunk = overlap_items
                current_length = sum(len(x) for x in current_chunk)

            current_chunk.append(item)
            current_length += item_len

        if current_chunk:
            joined = "".join(current_chunk).strip()
            if joined:
                final_chunks.append(joined)

        return final_chunks

class DocumentChunker:
    """Splits raw text sections into overlapping chunks attached with full metadata."""

    def __init__(self, chunk_size: int = 750, chunk_overlap: int = 100):
        self.chunk_size = max(50, chunk_size)
        if chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size - 20)
        else:
            self.chunk_overlap = max(0, chunk_overlap)

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
            keep_separator=True
        )

    def chunk_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes list of parsed document sections, splits text into chunks,
        and generates chunk-level metadata and UUIDs.
        """
        all_chunks = []

        for sec_idx, sec in enumerate(sections):
            text = sec.get("text", "")
            base_meta = sec.get("metadata", {})

            if not text.strip():
                continue

            splits = self.splitter.split_text(text)
            
            for chunk_idx, chunk_text in enumerate(splits):
                chunk_id = str(uuid.uuid4())
                chunk_meta = {
                    **base_meta,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_idx,
                    "total_chunks_in_section": len(splits),
                    "chunk_char_len": len(chunk_text)
                }

                all_chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "metadata": chunk_meta
                })

        return all_chunks
