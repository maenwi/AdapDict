"""
Verifier 공통 스키마 정의

- Verifier LLM(Gemini)의 출력 형식을 한 곳에서 정의한다.
- 쿼리 타입/모드에 상관없이, 모든 Verifier 호출은 이 스키마 하나만 사용한다.
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# =========================
# 타입 정의
# =========================

# (구버전 호환용) 이슈 심각도 타입
# - 예전 verifier 스키마에서 사용하던 타입으로,
#   현재 새로운 VerifierResult에서는 직접 사용하지 않는다.
IssueSeverity = Literal[
    "none",      # 이슈 없음
    "mild",      # 경미한 이슈
    "moderate",  # 중간 수준 이슈
    "severe",    # 심각한 이슈
]


# Hallucination 유형 (SenseDict에서 정의한 4가지 + 없음)
HallucinationType = Literal[
    "none",        # 할루시네이션 없음
    "semantic",    # Semantic Hallucination
    "factual",     # Factual Hallucination
    "contextual",  # Contextual Hallucination
    "translation", # Translation Hallucination (사전 모드에서만)
]


class VerifierMetadata(BaseModel):
    """
    (선택) Verifier 결과에 함께 기록할 메타데이터.
    - Verifier 자체의 로직에는 필수는 아니지만,
      로깅 / 분석 / 디버깅 시 편의를 위해 추가할 수 있다.
    """

    mode: Optional[str] = Field(
        default=None,
        description="AdapDict 모드 (정규화된 값: 'dict' 또는 'encyclopedia')",
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Query Analyzer가 판별한 쿼리 타입 (예: 'word', 'sentence', 'paragraph' 등)",
    )
    source_lang: Optional[str] = Field(
        default=None,
        description="입력 언어 코드 (예: 'ko', 'en'). 사전 모드에서만 사용 가능.",
    )
    target_lang: Optional[str] = Field(
        default=None,
        description="출력 언어 코드 (예: 'ko', 'en'). 사전 모드에서만 사용 가능.",
    )
    field: Optional[str] = Field(
        default=None,
        description="도메인/필드 정보 (예: 'technology', 'finance', 'science', 'general' 등)",
    )


class VerifierResult(BaseModel):
    """
    Verifier LLM의 최종 출력 포맷.

    - has_hallucination: Verifier가 볼 때 할루시네이션이 존재하는지 여부
    - hallucination_score: [0.0, 1.0] 범위의 연속 값
        * 0.0에 가까울수록 "거의 문제 없음"
        * 1.0에 가까울수록 "할루시네이션일 가능성이 높음"
    - type: 가장 대표적인 hallucination 유형 (없으면 "none")
    - comment: 내부 피드백용 한 줄 코멘트
        * has_hallucination == False 인 경우, 빈 문자열("")로 두는 것을 권장
        * 이 값은 유저에게 절대 노출되지 않고, main LLM 재생성 시 프롬프트에만 사용된다.
    """

    has_hallucination: bool = Field(
        ...,
        description="Verifier가 판단한 할루시네이션 존재 여부",
    )
    hallucination_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="할루시네이션 정도에 대한 Verifier의 확신도 (0.0 ~ 1.0)",
    )
    type: HallucinationType = Field(
        ...,
        description="가장 대표적인 hallucination 유형. 없으면 'none'.",
    )
    comment: str = Field(
        ...,
        description=(
            "내부 피드백용 한 줄 코멘트. "
            "유저에게는 절대 노출되지 않으며, main LLM 재생성 프롬프트에만 사용된다."
        ),
    )

    # (선택) 메타데이터 – 로깅/분석용
    metadata: Optional[VerifierMetadata] = Field(
        default=None,
        description="옵션: 모드, 쿼리 타입, 언어 방향 등의 메타데이터",
    )

    # =========================
    # 편의 메서드
    # =========================

    def is_safe(self, threshold: float) -> bool:
        """
        주어진 threshold 기준으로, 이 응답을 '안전(safe)'하다고 볼 수 있는지 여부.

        - threshold: 0.0 ~ 1.0
        - 관례적으로 hallucination_score <= threshold 이면 안전으로 본다.
        """
        return (not self.has_hallucination) or (self.hallucination_score <= threshold)

    def needs_regeneration(self, threshold: float) -> bool:
        """
        주어진 threshold 기준으로, main LLM의 재생성이 필요한지 여부.

        - 보통: hallucination_score > threshold 인 경우 재생성
        """
        return not self.is_safe(threshold)
