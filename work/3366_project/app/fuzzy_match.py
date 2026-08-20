"""Jamo-level fuzzy matching for ingredient names.

Splits Korean text into individual jamo (자모) so that visually/phonetically similar
misreads (OCR errors, typos) still score highly against the correct ingredient name.
Reused as-is once OCR input is wired in — for now it powers typo-tolerant search.
"""

import hgtk
from rapidfuzz import fuzz, process
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.product_ingredient import ProductIngredient

_jamo_cache: dict[int, str] = {}
_popularity_cache: dict[int, int] = {}


def _decompose(text: str) -> str:
    return hgtk.text.decompose(text)


def build_cache(db: Session) -> None:
    """Populate the in-memory jamo/popularity caches. Call once at startup."""
    rows = db.execute(select(Ingredient.ingredient_id, Ingredient.name_kr)).all()
    _jamo_cache.clear()
    _jamo_cache.update(
        {ingredient_id: _decompose(name_kr) for ingredient_id, name_kr in rows if name_kr}
    )

    popularity_rows = db.execute(
        select(ProductIngredient.ingredient_id, func.count()).group_by(
            ProductIngredient.ingredient_id
        )
    ).all()
    _popularity_cache.clear()
    _popularity_cache.update(dict(popularity_rows))


def search(query: str, limit: int = 20, threshold: float = 85.0) -> list[int]:
    """Return ingredient_ids whose jamo-decomposed name is >= threshold similar to query.

    Ties (equal similarity score) are broken by how often the ingredient shows up
    across products, on the assumption that a common ingredient is a likelier match
    than an obscure one with the same edit distance.
    """
    if not query or not _jamo_cache:
        return []

    query_jamo = _decompose(query)
    matches = process.extract(
        query_jamo,
        _jamo_cache,
        scorer=fuzz.ratio,
        limit=limit * 3,
        score_cutoff=threshold,
    )
    ranked = sorted(
        matches,
        key=lambda m: (m[1], _popularity_cache.get(m[2], 0)),
        reverse=True,
    )
    return [ingredient_id for _, _, ingredient_id in ranked[:limit]]
