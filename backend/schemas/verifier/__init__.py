# schemas/verifier/__init__.py

"""
schemas.verifier 패키지

- 새로운 VerifierResult 스키마만 외부로 노출한다.
- 예전 IssueSeverity / IssueCategory 등은 더 이상 사용하지 않는다.
"""

from __future__ import annotations

from .common import (
    HallucinationType,
    VerifierMetadata,
    VerifierResult,
)

__all__ = [
    "HallucinationType",
    "VerifierMetadata",
    "VerifierResult",
]
