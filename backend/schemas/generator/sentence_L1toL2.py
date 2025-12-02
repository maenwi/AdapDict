# schemas/sentence_L1toL2.py

from pydantic import BaseModel, Field
from typing import List, Optional

from .word import ExamplePair, LanguageCode
from .common import QueryAnalysisBlock

class SentenceL1toL2Block(BaseModel):
    """
    L1 → L2 문장 변환(번역/영작) 결과 블록.

    - l1_sentence: 사용자가 입력한 L1 문장
    - l1_lang   : 입력 문장의 언어 코드 (L1)
    - l2_lang   : 출력 문장의 언어 코드 (L2)
    - main_l2_sentence: L2로 옮긴 메인 문장 (가장 추천하는 결과)
    - alternative_l2_sentences: 메인 문장을 바탕으로 한 다른 L2 작문/표현들
    """

    # 입력 문장 (L1)
    l1_sentence: str = Field(
        description="Original user sentence in L1 (source language)."
    )
    l1_lang: LanguageCode = Field(
        description="Language code of L1 sentence, e.g. 'ko', 'en', 'zh', 'de'."
    )

    # 출력 문장 (L2)
    l2_lang: LanguageCode = Field(
        description="Language code of L2 sentence, e.g. 'en', 'ko', 'zh', 'de'."
    )
    main_l2_sentence: str = Field(
        description="Main L2 sentence as the primary translation/writing result."
    )

    # 추가 L2 작문/표현들 (옵션)
    alternative_l2_sentences: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional additional L2 sentences (alternative writings or paraphrases) "
            "based on the same L1 input."
        ),
    )


class L1toL2WordExplanationItem(BaseModel):
    """
    L2 기준 단어 해설 카드.

    - l2_word: L2 문장에서 추출한 단어/표현
    - meaning_l1: L1로 된 핵심 의미
    - explanation_l1: L1로 된 추가 설명/뉘앙스 (옵션)
    - examples: 예문 페어
        * example.source_sentence : L2 예문
        * example.target_sentence : L1 해석
    - alternatives_l2: L2 기준 유사/대체 표현
    """

    l2_word: str = Field(
        description="Token/word/expression taken from the L2 sentence."
    )

    meaning_l1: str = Field(
        description="Short meaning of the word in L1 (source language)."
    )

    explanation_l1: Optional[str] = Field(
        default=None,
        description="Optional nuance/explanation in L1.",
    )

    examples: Optional[List[ExamplePair]] = Field(
        default=None,
        description=(
            "Optional examples for the word. In L1→L2 sentence mode, "
            "example.source_sentence is in L2 and example.target_sentence is in L1."
        ),
    )

    alternatives_l2: Optional[List[str]] = Field(
        default=None,
        description="Optional alternative/similar expressions in L2.",
    )


class SentenceL1toL2Response(BaseModel):
    """
    L1 → L2 Sentence 모드 최상위 스키마.

    상단:
        - sentence: L1 입력 → L2 메인 문장 + 다른 L2 작문 문장들

    하단:
        - l2_focus_sentence: 단어 해설의 기준이 되는 L2 문장
            * 일반적으로 main_l2_sentence를 사용
        - word_explanations: l2_focus_sentence 안의 핵심 단어/표현 해설 리스트
    """
    query_analysis: QueryAnalysisBlock
    
    # 문장 결과 블록
    sentence: SentenceL1toL2Block = Field(
        description="Sentence-level L1→L2 translation/writing result."
    )

    # 단어 해설 기준이 되는 L2 문장
    l2_focus_sentence: str = Field(
        description=(
            "The L2 sentence used for extracting words (typically main_l2_sentence)."
        )
    )

    # 단어 해설 카드 리스트
    word_explanations: List[L1toL2WordExplanationItem] = Field(
        description="Explanations for key L2 words appearing in l2_focus_sentence."
    )
