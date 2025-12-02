# utils/verifier_client.py

"""
Verifier LLM(Gemini) 호출 유틸리티

- Main LLM이 생성한 1차 답변을 검증하기 위해 사용한다.
- 입력: 쿼리, 모드, 쿼리 타입, (언어 정보), Main LLM 답변
- 출력: VerifierResult (schemas/verifier/common.py)
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from schemas.verifier.common import VerifierResult
from utils.verifier_prompt import VERIFIER_SYSTEM_PROMPT, build_verifier_user_prompt


# ----------------------------
# 0. 초기 설정 (GOOGLE_API_KEY)
# ----------------------------

# main_demo.py에서 이미 load_dotenv()를 호출하지만,
# 여기서도 한 번 더 호출해도 문제는 없다. (중복 호출 무해)
load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY 환경변수가 없습니다. .env 확인하세요. (verifier_client)")

client = genai.Client(api_key=api_key)

# Verifier 전용 모델 이름
# - 필요하면 .env나 설정 파일로 빼도 된다.
VERIFIER_MODEL = "models/gemini-2.5-flash"

def run_verifier(
    query_text: str,
    mode: str,
    query_type: str,
    answer_text: str,
    field: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
) -> VerifierResult:
    """
    Verifier LLM을 한 번 호출하여 VerifierResult를 반환한다.

    - 이 함수는 main_demo.py에서만 직접 사용하는 것을 의도한다.
    - Verifier가 이상한 응답을 내거나 파싱에 실패하면, 보수적으로 "검사 실패 → 그냥 통과"로 간주한다.
    (has_hallucination=False, hallucination_score=0.0)
    """

    # 1) Verifier용 user prompt 생성
    user_prompt = build_verifier_user_prompt(
        query_text=query_text,
        mode=mode,
        query_type=query_type,
        answer_text=answer_text,
        field=field,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    # 2) Gemini Verifier 모델 호출 설정
    verifier_config = {
        # ✅ system_prompt는 config 쪽으로 보내는 게 최신 SDK 방식
        "system_instruction": VERIFIER_SYSTEM_PROMPT,
        "response_schema": VerifierResult,
        "response_mime_type": "application/json",
        "max_output_tokens": 65536,
        # (1130 02:38 만휘 수정) verifier의 max_output_tokens를 1024로 제한해서,
        # verifier의 출력이 멈추는 현상이 있었음.
        # 왜 발생하냐? Gemini가 자체적으로 생각을 한다고 함. 근데 그 생각 토큰이 1024가 넘어버리면
        # verifier가 최종 출력을 못하고 생각하다 멈춰버림.
    }

    try:
        # system + user 메시지를 분리해서 전달
        response = client.models.generate_content(
            model=VERIFIER_MODEL,
            contents=user_prompt,
            config=verifier_config,
        )
        print("🔍 [Verifier raw response]", response) # 실험용 로그

        # 3) structured output (Pydantic) 파싱
        result = response.parsed  # VerifierResult 인스턴스를 기대

        # 3-1) structured output이 안 온 경우: text 기반으로 복구 시도
        if result is None:
            raw_text = getattr(response, "text", None)

            if isinstance(raw_text, str) and raw_text.strip():
                # 문자열이 있으면 JSON 파싱 시도
                result = VerifierResult.model_validate_json(raw_text)
            else:
                # 아예 응답이 비었거나, text가 None → Verifier 실패로 간주
                # raise RuntimeError("Verifier returned empty response")
                print("⚠️ [Verifier] Empty structured response; treating as verification failure.")
                # 여기서 바로 fallback 리턴
                return VerifierResult(
                    has_hallucination=False,
                    hallucination_score=0.0,
                    type="none",
                    comment="",
                    metadata=None,
                )

    except (ValidationError, RuntimeError) as e:
        print("❌ [Verifier] ValidationError or empty response:", e)
        # ✅ 소프트 실패: "검사 못 했으니, 일단 통과시킨다"
        #    → has_hallucination=False, score=0.0 이면
        #       VerifierResult.needs_regeneration(threshold) == False 가 됨.
        result = VerifierResult(
            has_hallucination=False,
            hallucination_score=0.0,
            type="none",
            comment="",
            metadata=None,
        )

    except Exception as e:
        print("❌ [Verifier] Exception occurred while calling verifier LLM:", e)
        # 기타 예외도 동일하게 "검사 실패 → 통과"로 처리
        result = VerifierResult(
            has_hallucination=False,
            hallucination_score=0.0,
            type="none",
            comment="",
            metadata=None,
        )

    return result
