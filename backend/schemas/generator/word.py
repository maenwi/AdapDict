# schemas/word.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from .common import QueryAnalysisBlock

# ExamplePair : 예문과 뜻 처리하는 단위
# WordSenseVariant : 한 단어/구가 여러 뜻을 가질 수 있고, 각 뜻을 처리하는 단위
# WordDictEntry : 한 단어/구가 가진 각 뜻을 WordSenseVariant가 모델링 했으면, 얘가 하나의 카드로 모아줌
# WordDictResponse : 여러 단어/구를 처리하기 위해 각 단어/구 카드를 관리

LanguageCode = Literal["en", "ko", "zh", "de"]

class ExamplePair(BaseModel):
    """
    예문 페어.
    - source_sentence: SOURCE 언어 예문
    - target_sentence: TARGET 언어 번역/대응 예문
    """
    source_sentence: str = Field(
        description="Example sentence in the SOURCE language (same as parent source_lang)."
    )
    target_sentence: str = Field(
        description="Corresponding sentence in the TARGET language (same as parent target_lang)."
    )

class WordSenseVariant(BaseModel):
    """
    단어/구에 대한 하나의 '뜻/용법' 블록.
    - target_text: TARGET 언어로 된 의미/표현
    - explanation: SOURCE 언어로 된 추가 설명/뉘앙스
    - examples: SOURCE↔TARGET 예문 페어
    - alternatives: TARGET 언어로 된 유사/대체 표현
    """
    target_text: str = Field(
        description="Meaning or expression in the TARGET language."
    )

    explanation: Optional[str] = Field(
        default=None,
        description="Optional explanation, typically in the SOURCE language."
    )

    examples: Optional[List[ExamplePair]] = Field(
        default=None,
        description="Optional example sentence pairs (SOURCE→TARGET)."
    )

    alternatives: Optional[List[str]] = Field(
        default=None,
        description="Optional alternative/similar expressions in the TARGET language."
    )

class WordDictEntry(BaseModel):
    """
    단어/구 사전 엔트리 (dictionary_word 전용).
    """
    source_text: str = Field(
        description="Original user input chunk (word or phrase) in the SOURCE language."
    )

    source_lang: LanguageCode = Field(
        description="Language code of the source text, e.g. 'en', 'ko', 'zh', 'de'."
    )

    target_lang: LanguageCode = Field(
        description="Language code of the target text, e.g. 'ko', 'en', 'zh', 'de'."
    )

    variants: List[WordSenseVariant] = Field(
        description="List of sense variants (different meanings/usages) for this word/phrase."
    )

class WordDictResponse(BaseModel):
    query_analysis: QueryAnalysisBlock # 공통: 쿼리 유효성 분석 결과
    entries: List[WordDictEntry] = Field(
        description="List of word/phrase entries (for possibly multiple inputs)."
    )
