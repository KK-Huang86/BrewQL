"""Knowledge documents for RAG (rag-knowledge-base): load and validate the YAML files in the repo.

Three files, one per kind: schema.yaml and glossary.yaml hold {id, title, content}; examples.yaml holds
{id, question, sql}, where the question becomes the title and the SQL the content. Documents describe
the data, never rows of it.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from app.sql_guard import SqlGuardError, validate_sql

KnowledgeKind = Literal["schema", "glossary", "example"]

# backend/knowledge: the documents the importer embeds.
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

# File name, kind, and the keys each entry must have besides id; order is the load order.
_FILES: tuple[tuple[str, KnowledgeKind, tuple[str, ...]], ...] = (
    ("schema.yaml", "schema", ("title", "content")),
    ("glossary.yaml", "glossary", ("title", "content")),
    ("examples.yaml", "example", ("question", "sql")),
)


class KnowledgeError(ValueError):
    """A knowledge file is unusable; the message names the file or document at fault."""


@dataclass(frozen=True)
class KnowledgeDoc:
    id: str
    kind: KnowledgeKind
    title: str
    content: str


def load_knowledge(directory: Path) -> list[KnowledgeDoc]:
    docs: list[KnowledgeDoc] = []
    seen: set[str] = set()
    for name, kind, keys in _FILES:
        for doc in _load_file(Path(directory) / name, kind, keys):
            if doc.id in seen:
                raise KnowledgeError(f"{doc.id}: duplicate id")
            seen.add(doc.id)
            docs.append(doc)
    return docs


def _load_file(path: Path, kind: KnowledgeKind, keys: tuple[str, ...]) -> list[KnowledgeDoc]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        # A missing file must not read as "delete every document of this kind".
        raise KnowledgeError(f"cannot read {path.name}: {e}") from e
    except yaml.YAMLError as e:
        raise KnowledgeError(f"{path.name} is not valid YAML: {e}") from e
    if not isinstance(data, list):
        raise KnowledgeError(f"{path.name} must be a list (use [] for none)")
    return [_parse(entry, f"{path.name} entry {index}", kind, keys) for index, entry in enumerate(data, start=1)]


def _parse(entry: object, where: str, kind: KnowledgeKind, keys: tuple[str, ...]) -> KnowledgeDoc:
    if not isinstance(entry, dict):
        raise KnowledgeError(f"{where}: must be a mapping")
    doc_id = entry.get("id")
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise KnowledgeError(f"{where}: missing id")
    doc_id = doc_id.strip()
    unknown = set(entry) - {"id", *keys}
    if unknown:
        raise KnowledgeError(f"{doc_id}: unknown keys {', '.join(sorted(unknown))}")
    values = []
    for key in keys:
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            raise KnowledgeError(f"{doc_id}: missing {key}")
        values.append(value.strip())
    title, content = values
    if kind == "example":
        try:
            validate_sql(content)
        except SqlGuardError as e:
            # An example teaches the model; one the guard would reject teaches it to fail.
            raise KnowledgeError(f"{doc_id}: example SQL rejected by the guard: {e}") from e
    return KnowledgeDoc(id=doc_id, kind=kind, title=title, content=content)
