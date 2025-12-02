# schemas/generator/__init__.py

# Word dictionary
from .word import WordDictResponse

# Encyclopedia mode
from .encyclopedia import EncyclopediaResponse

# Sentence modes
from .sentence_L1toL2 import SentenceL1toL2Response
from .sentence_L2toL1 import SentenceL2toL1Response

# Paragraph modes
from .paragraph_L1toL2 import ParagraphL1toL2Response
from .paragraph_L2toL1 import ParagraphL2toL1Response


__all__ = [
    # word dict
    "WordDictResponse",

    # encyclopedia
    "EncyclopediaResponse",

    # sentence
    "SentenceL1toL2Response",
    "SentenceL2toL1Response",

    # paragraph
    "ParagraphL1toL2Response",
    "ParagraphL2toL1Response",
]
