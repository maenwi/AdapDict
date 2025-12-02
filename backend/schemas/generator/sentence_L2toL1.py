# schemas/sentence_L2toL1.py

from pydantic import BaseModel, Field
from typing import List, Optional

from .word import ExamplePair, LanguageCode
from .common import QueryAnalysisBlock


class SentenceL2toL1Block(BaseModel):
    """
    L2 → L1 문장 해석 결과 블록.

    시나리오:
    - 사용자가 공부 언어(L2)로 문장을 입력하면,
        - main_l1_sentence: L1로 된 '한 줄 해석'을 제공하고
        - sentence_explanation_l1: L1로, 이 문장의 의미를 설명한다.
    """
    
    query_analysis: QueryAnalysisBlock

    # 입력 문장 (L2)
    l2_sentence: str = Field(
        description="Original user sentence in L2 (target/learning language)."
    )
    l2_lang: LanguageCode = Field(
        description="Language code of the L2 sentence, e.g. 'en', 'ko', 'zh', 'de'."
    )

    # 출력/해석 문장 (L1)
    l1_lang: LanguageCode = Field(
        description="Language code of L1 (user's native/source language), e.g. 'ko', 'en', 'zh', 'de'."
    )
    main_l1_sentence: str = Field(
        description="Single-sentence interpretation/translation of the L2 sentence in L1."
    )

    # 문맥/뉘앙스/용법 설명 (L1)
    sentence_explanation_l1: Optional[str] = Field(
        default=None,
        description=(
            "Optional explanation in L1 describing the overall meaning or content of the L2 sentence. "
            "Used instead of listing multiple alternative translations."
        ),
    )




class L2toL1WordExplanationItem(BaseModel):
    """
    L2 문장에서 추출한 핵심 단어/표현에 대한 해설 카드.

    - l2_word        : L2 문장에서 뽑은 단어/표현
    - meaning_l1     : L1로 된 핵심 의미
    - explanation_l1 : L1로 된 추가 설명/뉘앙스 (선택)
    - examples       : 예문 페어
        * example.source_sentence : L2 예문
        * example.target_sentence : L1 해석
    - alternatives_l2: L2 기준 유사/대체 표현
    """

    l2_word: str = Field(
        description="Token/word/expression taken from the L2 sentence."
    )

    meaning_l1: str = Field(
        description="Short meaning of the word in L1 (native/source language)."
    )

    explanation_l1: Optional[str] = Field(
        default=None,
        description="Optional nuance/explanation in L1.",
    )

    examples: Optional[List[ExamplePair]] = Field(
        default=None,
        description=(
            "Optional examples for the word. In L2→L1 sentence mode, "
            "example.source_sentence is in L2 and example.target_sentence is in L1."
        ),
    )

    alternatives_l2: Optional[List[str]] = Field(
        default=None,
        description="Optional alternative/similar expressions in L2.",
    )


class SentenceL2toL1Response(BaseModel):
    """
    L2 → L1 Sentence 모드 최상위 스키마.

    상단:
        - sentence: L2 입력 → L1 한 줄 해석 + L1로 된 문장 내용 설명

    하단:
        - l2_focus_sentence: 단어 해설의 기준이 되는 L2 문장
            * 일반적으로 사용자가 입력한 l2_sentence를 그대로 사용
        - word_explanations: l2_focus_sentence 안의 핵심 단어/표현 해설 리스트
    """

    # 문장 해석 결과 블록
    sentence: SentenceL2toL1Block = Field(
        description="Sentence-level L2→L1 interpretation/translation result."
    )

    # 단어 해설 기준이 되는 L2 문장
    l2_focus_sentence: str = Field(
        description=(
            "The L2 sentence used for extracting words (typically the original user input l2_sentence)."
        )
    )

    # 단어 해설 카드 리스트
    word_explanations: List[L2toL1WordExplanationItem] = Field(
        description="Explanations for key L2 words appearing in l2_focus_sentence."
    )
