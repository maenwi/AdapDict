# schemas/__init__.py

# Re-export generator outputs
from .generator import (
    WordDictResponse,
    EncyclopediaResponse,
    SentenceL1toL2Response,
    SentenceL2toL1Response,
    ParagraphL1toL2Response,
    ParagraphL2toL1Response,
)


__all__ = [
    # generator outputs
    "WordDictResponse",
    "EncyclopediaResponse",
    "SentenceL1toL2Response",
    "SentenceL2toL1Response",
    "ParagraphL1toL2Response",
    "ParagraphL2toL1Response",
]
