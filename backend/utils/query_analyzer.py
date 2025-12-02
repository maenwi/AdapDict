# query_analyzer.py

from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import re


LangCode = Literal["ko", "en", "zh", "de"]
QueryType = Literal["word", "word_list", "phrase", "phrase_list", "sentence", "paragraph"]


class QueryAnalysisResult(BaseModel):
    """
    Model A-1: Query Analyzer 결과 스키마.

    - raw_query: 사용자가 입력한 원문 (trim 전)
    - normalized_query: 기본 전처리(공백/줄바꿈 정리) 후 텍스트
    - query_type: 6가지 타입 중 하나
    - units: 쪼개진 단위 리스트
        - word        -> ["protein"]
        - word_list   -> ["protein", "water", "DNA"]
        - phrase      -> ["at the end of the day"]
        - phrase_list -> ["in a nutshell", "at the end of the day", ...]
        - sentence    -> ["I studied protein."]
        - paragraph   -> ["문장1", "문장2", ...]
    - query_lang: 실제 입력 언어 (native_lang or target_lang 중 하나로 매핑)
    """
    raw_query: str = Field(..., description="원본 입력 문자열 (strip 이전).")
    normalized_query: str = Field(..., description="공백/줄바꿈 정리 후 텍스트.")
    query_type: QueryType = Field(..., description="분류된 쿼리 타입.")
    units: List[str] = Field(..., description="분할된 단위 리스트.")
    query_lang: Optional[LangCode] = Field(
        default=None,
        description="실제 입력 언어 (native_lang 또는 target_lang)."
    )


# ============================
#   내부 유틸 함수들
# ============================

_CJK_RANGE = re.compile(r"[\u4E00-\u9FFF]")
_HANGUL_RANGE = re.compile(r"[\uAC00-\uD7A3]")
_LATIN_RANGE = re.compile(r"[A-Za-z]")
_GERMAN_CHAR = re.compile(r"[ÄÖÜäöüß]")
_SENT_TERM_LATIN = re.compile(r"[\.!?]")
_SENT_TERM_ZH = re.compile(r"[。？！]")
_LIST_SPLIT_PATTERN = re.compile(r"[;,/·]|[，、；]|\n+")


def _normalize(text: str) -> str:
    # strip + 줄바꿈/공백 정리
    if text is None:
        return ""
    # 통일된 개행
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # 양쪽 공백 제거
    t = t.strip()
    # 연속 공백 → 하나
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _lang_score(text: str, lang: LangCode) -> int:
    """
    native_lang / target_lang 중 어느 쪽 비중이 더 큰지 비교하기 위한 점수.
    각 언어에 대응하는 문자 유형 개수를 기반으로 한다.
    """
    if not text:
        return 0

    sample = text[:300]

    if lang == "ko":
        return len(_HANGUL_RANGE.findall(sample))
    if lang == "zh":
        return len(_CJK_RANGE.findall(sample))
    if lang == "de":
        # 독일어: 특수문자 + 라틴 문자 모두 반영
        return len(_GERMAN_CHAR.findall(sample)) + len(_LATIN_RANGE.findall(sample))
    if lang == "en":
        return len(_LATIN_RANGE.findall(sample))

    return 0


def _looks_like_paragraph(text: str, lang: Optional[LangCode]) -> bool:
    """
    여러 문장이면서 길이가 긴 경우 paragraph로 본다.
    """
    if not text:
        return False

    # 문장 종결부호 기준 대략 split
    if lang == "zh":
        parts = _SENT_TERM_ZH.split(text)
    else:
        parts = _SENT_TERM_LATIN.split(text)

    # 공백/빈 문자열 제거
    sentences = [p.strip() for p in parts if p.strip()]
    if len(sentences) < 2:
        return False

    length = len(text)
    if length < 80:
        return False

    return True


def _split_sentences(text: str, lang: Optional[LangCode]) -> List[str]:
    """
    paragraph일 때 문장 리스트로 쪼갤 때 사용.
    아주 단순한 문장 segmentation.
    """
    if not text:
        return []

    if lang == "zh":
        # 중국어: 。？！ 기준
        parts = re.split(r"(?<=[。？！])\s*", text)
    else:
        # 기타: .?! 기준
        parts = re.split(r"(?<=[\.!?])\s+", text)

    sentences = [p.strip() for p in parts if p.strip()]
    return sentences


def _split_list_candidates(text: str) -> List[str]:
    """
    리스트 후보를 쪼갤 때 사용하는 함수.
    콤마/세미콜론/중국어 열거 부호/줄바꿈 등을 기준으로 분리.
    """
    items = _LIST_SPLIT_PATTERN.split(text)
    items = [it.strip() for it in items if it.strip()]
    return items


def _has_sentence_punc(text: str, lang: Optional[LangCode]) -> bool:
    if lang == "zh":
        return bool(_SENT_TERM_ZH.search(text))
    return bool(_SENT_TERM_LATIN.search(text))


def _is_word_like(unit: str, lang: Optional[LangCode]) -> bool:
    """
    대략적인 '단어 느낌' 판단:
    - 영어/독어: 공백 없음
    - 한국어: 공백 없음
    - 중국어: 글자 수 <= 3
    """
    if not unit:
        return False

    if lang in ("en", "de"):
        if re.search(r"\s", unit):
            return False
        return len(unit) <= 32

    if lang == "ko":
        return not re.search(r"\s", unit)

    if lang == "zh":
        stripped = re.sub(r"\s", "", unit)
        return len(stripped) <= 3

    return not re.search(r"\s", unit)


def _decide_list_type(items: List[str], lang: Optional[LangCode]) -> QueryType:
    """
    리스트 항목들을 보고 word_list / phrase_list 결정.
    """
    if not items:
        return "word_list"

    word_like_count = sum(1 for it in items if _is_word_like(it, lang))
    ratio = word_like_count / len(items)

    if ratio >= 0.7:
        return "word_list"
    return "phrase_list"


def _looks_like_sentence(text: str, lang: Optional[LangCode]) -> bool:
    """
    단일 유닛일 때 sentence인지 phrase/word인지 판정.
    """
    if not text:
        return False

    stripped = text.strip()

    # --- 한국어 전용: 마침표가 없어도 '문장 어미' 패턴이면 문장으로 본다 ---
    if lang == "ko" and not _has_sentence_punc(stripped, lang):
        # 너무 짧은 건 문장으로 안 본다 (예: "좋다", "맞음")
        if len(stripped) >= 10:
            # 자주 쓰는 문장 어미 패턴들
            # ...다 / ...이다 / ...했다 / ...합니다 / ...했어요 / ...인가요 / ...인가 / ...네요 / ...군요 / ...겠어요 / ...겠습니
            if re.search(r"(다|이다|했다|합니다|했습니다|했어요|입니다|입니 다|인가요|인가요?|인가|인가요|네요|군요|겠어요|겠습니다)[\"'’”\)\s]*$", stripped):
                return True

    # --- 기존: 종결부호가 있으면 우선 문장 후보 ---
    if _has_sentence_punc(stripped, lang):
        tokens = stripped.split()
        if len(tokens) >= 3:
            return True
        if lang in ("ko", "zh") and len(stripped) >= 10:
            return True

    # --- 일반적인 길이 기반 heuristic ---
    tokens = stripped.split()
    if len(tokens) >= 6 and len(stripped) >= 40:
        return True

    if lang == "zh":
        no_space = re.sub(r"\s", "", stripped)
        if len(no_space) >= 20:
            return True

    return False



def _decide_word_or_phrase(text: str, lang: Optional[LangCode]) -> QueryType:
    """
    sentence가 아니라고 확정된 상태에서 word / phrase 결정.
    """
    if not text:
        return "word"

    if lang in ("en", "de", "ko"):
        tokens = text.split()
        if len(tokens) <= 1:
            return "word"
        return "phrase"

    if lang == "zh":
        stripped = re.sub(r"\s", "", text)
        if len(stripped) <= 3:
            return "word"
        return "phrase"

    tokens = text.split()
    if len(tokens) <= 1:
        return "word"
    return "phrase"


# ============================
#   Public API
# ============================

def analyze_query(
    query: str,
    native_lang: LangCode,
    target_lang: LangCode,
) -> QueryAnalysisResult:
    """
    Model A-1: Query Analyzer 메인 함수.
    """

    raw_query = query or ""
    normalized = _normalize(raw_query)

    if not normalized:
        raise ValueError("QueryAnalyzer: query가 비어 있습니다.")

    # 1) native_lang / target_lang 중 실제 텍스트에서 비중이 더 큰 언어를 기준으로 query_lang 설정
    native_score = _lang_score(normalized, native_lang)
    target_score = _lang_score(normalized, target_lang)

    if native_score > 0 or target_score > 0:
        if native_score > target_score:
            query_lang: Optional[LangCode] = native_lang
        elif target_score > native_score:
            query_lang = target_lang
        else:
            query_lang = native_lang
    else:
        query_lang = native_lang

    lang_for_heuristics: Optional[LangCode] = query_lang
    text = normalized

    # 3) paragraph 후보인지 먼저 판단
    if _looks_like_paragraph(text, lang_for_heuristics):
        sentences = _split_sentences(text, lang_for_heuristics)
        if sentences:
            return QueryAnalysisResult(
                raw_query=raw_query,
                normalized_query=normalized,
                query_type="paragraph",
                units=sentences,
                query_lang=query_lang,
            )

    # 4) 리스트 후보인지 판단
    list_items = _split_list_candidates(text)
    if len(list_items) >= 2:
        sentence_like_count = sum(
            1 for it in list_items if _looks_like_sentence(it, lang_for_heuristics)
        )
        if sentence_like_count == 0:
            list_type = _decide_list_type(list_items, lang_for_heuristics)
            return QueryAnalysisResult(
                raw_query=raw_query,
                normalized_query=normalized,
                query_type=list_type,
                units=list_items,
                query_lang=query_lang,
            )

    # 5) 단일 유닛 (word / phrase / sentence)
    if _looks_like_sentence(text, lang_for_heuristics):
        qtype: QueryType = "sentence"
    else:
        qtype = _decide_word_or_phrase(text, lang_for_heuristics)

    return QueryAnalysisResult(
        raw_query=raw_query,
        normalized_query=normalized,
        query_type=qtype,
        units=[text],
        query_lang=query_lang,
    )
