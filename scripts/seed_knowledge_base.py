"""Load knowledge_base/*.md into the knowledge_base table, one row per ## entry.

Run with: uv run python -m scripts.seed_knowledge_base
Re-running updates existing rows (matched on section + title) instead of adding new ones.
"""

from pathlib import Path

from app import db

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


def parse(path: Path) -> list[tuple[str, str, str]]:
    """Split a Markdown file into (section, title, content) tuples, one per ## heading."""
    chunks = path.read_text(encoding="utf-8").split("\n## ")
    entries = []
    for chunk in chunks[1:]:  # chunks[0] is the "# Heading" preamble
        title, _, content = chunk.partition("\n")
        entries.append((path.stem, title.strip(), content.strip()))
    return entries


if __name__ == "__main__":
    with db.connect() as conn:
        for path in sorted(KB_DIR.glob("*.md")):
            entries = parse(path)
            for section, title, content in entries:
                conn.execute(
                    """
                    insert into knowledge_base (section, title, content)
                    values (%s, %s, %s)
                    on conflict (section, title) do update
                      set content = excluded.content, updated_at = now()
                    """,
                    (section, title, content),
                )
            print(f"{path.stem}: {len(entries)} entries")
