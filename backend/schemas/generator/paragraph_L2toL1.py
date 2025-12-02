# schemas/paragraph_L2toL1.py

from pydantic import BaseModel, Field
from typing import List, Optional

from .word import LanguageCode
from .sentence_L2toL1 import SentenceL2toL1Response
from .common import QueryAnalysisBlock


class ParagraphL2toL1Response(BaseModel):
    """
    L2 → L1 문단 처리 스키마.

    - 입력: L2 문단 전체 (문장 여러 개)
    - 출력:
        * l2_paragraph                 : 원래 L2 문단
        * l2_lang, l1_lang             : 언어 코드
        * paragraph_l1_translation     : 문단 전체에 대한 L1 번역 (통 번역)
        * paragraph_content_explanation_l1 : 문단 내용에 대한 L1 설명
        * sentence_cards               : 각 문장에 대한 SentenceL2toL1Response 카드 리스트

    구현 관점:
    - 문단 번역과 문장 번역이 최대한 일관되도록 생성해야 한다.
        (예: 문단 전체 번역을 기준으로 문장별 결과를 정렬하거나,
        문장 번역을 만든 뒤 이어 붙여 문단 번역을 구성하는 방식 등)
    """
    query_analysis: QueryAnalysisBlock

    # 입력 문단 (L2)
    l2_paragraph: str = Field(
        description="Original paragraph text in L2 (learning/target language)."
    )
    l2_lang: LanguageCode = Field(
        description="Language code of L2, e.g. 'en', 'ko', 'zh', 'de'."
    )

    # 출력 언어 (L1)
    l1_lang: LanguageCode = Field(
        description="Language code of L1 (native/source language), e.g. 'ko', 'en', 'zh', 'de'."
    )

    # 문단 전체 번역 (L1)
    paragraph_l1_translation: str = Field(
        description="Full-paragraph translation into L1."
    )

    # 문단 내용 설명 (L1)
    paragraph_content_explanation_l1: Optional[str] = Field(
        default=None,
        description=(
            "Optional explanation in L1 describing the overall meaning or content "
            "of the entire L2 paragraph."
        ),
    )

    # 문장 단위 카드 리스트
    sentence_cards: List[SentenceL2toL1Response] = Field(
        description=(
            "Per-sentence cards for the paragraph, each built using the L2→L1 "
            "sentence schema (SentenceL2toL1Response). The paragraph is treated as "
            "a list of sentences."
        )
    )
