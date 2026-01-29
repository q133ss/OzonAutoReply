import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from .db import Database


def _normalize_example(raw: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
    product_title = (raw.get("product_title") or "").strip()
    text = (raw.get("text") or "").strip()
    example_response = (raw.get("example_response") or "").strip()
    rating = raw.get("rating")
    try:
        rating = int(rating)
    except Exception:
        rating = 0

    if not product_title:
        return False, {}, "missing product_title"
    if rating < 1 or rating > 5:
        return False, {}, "rating must be 1..5"
    if not text:
        return False, {}, "missing text"
    if not example_response:
        return False, {}, "missing example_response"

    return True, {
        "product_title": product_title,
        "rating": rating,
        "text": text,
        "example_response": example_response,
    }, ""


def _load_examples(path: Path) -> Iterable[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("examples"), list):
        return payload["examples"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Invalid JSON structure; expected {\"examples\": [...]} or a list.")


def import_examples(db_path: Path, json_path: Path, replace: bool = False) -> int:
    examples = list(_load_examples(json_path))
    if not examples:
        return 0

    db = Database(str(db_path))
    try:
        if replace:
            cur = db.conn.cursor()
            cur.execute("DELETE FROM ai_examples")
            db.conn.commit()

        inserted = 0
        for raw in examples:
            if not isinstance(raw, dict):
                continue
            ok, data, error = _normalize_example(raw)
            if not ok:
                print(f"skip: {error}: {raw}")
                continue
            db.save_example(data)
            inserted += 1
        return inserted
    finally:
        db.close()


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Import AI examples from JSON into ozon_ai.db")
    parser.add_argument(
        "--db-path",
        default=str(base_dir / "ozon_ai.db"),
        help="Path to sqlite database (default: ozon_ai.db in project root)",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(base_dir / "ozon_ai" / "data" / "ai_examples_seed.json"),
        help="Path to JSON with examples",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing examples before import",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    json_path = Path(args.json_path)
    if not json_path.exists():
        raise SystemExit(f"JSON not found: {json_path}")

    inserted = import_examples(db_path, json_path, replace=args.replace)
    print(f"Imported: {inserted}")


if __name__ == "__main__":
    main()
