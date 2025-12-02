# schemas/paragraph_L1toL2.py

from pydantic import BaseModel, Field
from typing import List

from .word import LanguageCode
from .sentence_L1toL2 import SentenceL1toL2Response
from .common import QueryAnalysisBlock


class ParagraphL1toL2Response(BaseModel):
    """
    L1 → L2 문단 처리 스키마.

    - 입력: L1 문단 전체 (문장 여러 개)
    - 출력:
        * l1_paragraph: 원래 L1 문단 (그대로 보관)
        * l1_lang, l2_lang: 언어 코드
        * sentence_cards: 각 문장에 대한 SentenceL1toL2Response 카드 리스트

    문단은 "문장 리스트"로만 처리하고,
    별도의 문단 전체 번역 텍스트는 강제하지 않는다.
    (필요하면 sentence_cards 안의 main_l2_sentence들을 이어 붙여서 구성 가능)
    """
    query_analysis: QueryAnalysisBlock  # 공통: 쿼리 유효성 분석 결과

    # 입력 문단 (L1)
    l1_paragraph: str = Field(
        description="Original paragraph text in L1 (source language)."
    )
    l1_lang: LanguageCode = Field(
        description="Language code of L1, e.g. 'ko', 'en', 'zh', 'de'."
    )

    # 출력 언어 (L2)
    l2_lang: LanguageCode = Field(
        description="Language code of L2, e.g. 'en', 'ko', 'zh', 'de'."
    )

    # 문장 단위 카드 리스트
    sentence_cards: List[SentenceL1toL2Response] = Field(
        description=(
            "Per-sentence cards for the paragraph, each built using the L1→L2 "
            "sentence schema (SentenceL1toL2Response). "
            "The paragraph is treated as a list of sentences."
        )
    )
