# main_demo.py

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import traceback
import json
from typing import Any, Optional


from google import genai

# A-1: Query Analyzer
from utils.query_analyzer import analyze_query, LangCode

# A-2: Rule-based Prompt Composer
from prompt_rule import generate_prompt_rule

# Verifier 클라이언트
from utils.verifier_client import run_verifier
from schemas.verifier.common import VerifierResult

# Structured output schemas (Generator 응답 스키마)
from schemas import (
    WordDictResponse,
    EncyclopediaResponse,
    SentenceL1toL2Response,
    SentenceL2toL1Response,
    ParagraphL1toL2Response,
    ParagraphL2toL1Response,
)

# ----------------------------
# 0. 초기 설정
# ----------------------------
load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY 환경변수가 없습니다. .env 확인하세요.")

client = genai.Client(api_key=api_key)

# Verifier threshold (hallucination_score 기준)
VERIFIER_HALLUCINATION_THRESHOLD = 0.4

# Flask app + 정적/템플릿 경로 설정
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
CORS(app)

# ----------------------------
# 1. 프론트엔드 라우트
# ----------------------------

@app.route("/")
def index_page():
    return render_template("index.html")

@app.route("/result")
def result_page():
    return render_template("results.html")

# ----------------------------
# 2. 스키마 선택 함수
# ----------------------------

def select_schema(mode, analysis, native_lang):
    """
    mode, query_type, native_lang에 따라
    LLM structured output에 사용할 Pydantic 스키마를 선택한다.
    """
    if mode == "encyclopedia":
        generator_schema = EncyclopediaResponse
    else:
        # 사전 모드
        if analysis.query_type in ["word", "word_list", "phrase", "phrase_list"]:
            generator_schema = WordDictResponse

        elif analysis.query_type in ["sentence"]:
            if native_lang == analysis.query_lang:
                # L1 → L2 문장 모드
                generator_schema = SentenceL1toL2Response
            else:
                # L2 → L1 문장 모드
                generator_schema = SentenceL2toL1Response

        else:
            # 문단 모드
            if native_lang == analysis.query_lang:
                # L1 → L2 문단
                generator_schema = ParagraphL1toL2Response
            else:
                # L2 → L1 문단
                generator_schema = ParagraphL2toL1Response

    return generator_schema

def build_verifier_answer_text(entry: Any, mode: str, query_type: str) -> str:
    """
    Verifier에 넘길 answer_text를 모드/쿼리 타입별로 요약해서 만든다.

    설계 원칙 (우선순위 → 뒤에 있는 것일수록 길이 제한에서 먼저 잘림):

    - WordDictResponse:
        1순위: source_text/lang, 각 variant의 target_text + explanation
        2순위: 각 variant의 alternatives, 예문 1쌍
        3순위: 추가 예문, 뒤쪽 variants

    - SentenceL1toL2Response (L1 → L2 문장):
        1순위: l1_sentence, main_l2_sentence
        2순위: word_explanations의 l2_word, meaning_l1, explanation_l1
        3순위: alternative_l2_sentences, word_explanations의 examples, alternatives_l2

    - SentenceL2toL1Response (L2 → L1 문장):
        1순위: l2_sentence, main_l1_sentence, sentence_explanation_l1
        2순위: word_explanations의 l2_word, meaning_l1, explanation_l1
        3순위: word_explanations의 examples, alternatives_l2

    - ParagraphL1toL2Response (L1 → L2 문단):
        1순위: l1_paragraph, 각 문장의 l1_sentence + main_l2_sentence
        2순위: 각 sentence card의 word_explanations (특히 meaning_l1, explanation_l1)
        3순위: word_explanations의 examples/alternatives, alternative_l2_sentences

    - ParagraphL2toL1Response (L2 → L1 문단):
        1순위: l2_paragraph, paragraph_l1_translation, paragraph_content_explanation_l1,
               각 문장의 l2_sentence + main_l1_sentence(+ sentence_explanation_l1)
        2순위: 각 sentence card의 word_explanations (word/meaning/explanation)
        3순위: word_explanations의 examples/alternatives

    - EncyclopediaResponse:
        1순위: simplified_explanation, key_terms.term/definition
        2순위: input_text, usage_context
        3순위: key_terms.analogy, extra_notes
    """

    # entry를 dict으로 변환
    try:
        data = entry.model_dump()
    except Exception:
        data = entry

    lines: list[str] = []
    mode_norm = (mode or "").strip().lower()
    qtype = (query_type or "").strip().lower()

    # -------------------------
    # 공통 헤더 + query_analysis
    # -------------------------
    lines.append("[AdapDict answer summary for Verifier]")
    lines.append(f"mode={mode_norm}, query_type={qtype}")

    qa_dict = None
    if isinstance(data, dict):
        if "query_analysis" in data:
            qa_dict = data.get("query_analysis")
        elif isinstance(data.get("sentence"), dict) and "query_analysis" in data["sentence"]:
            qa_dict = data["sentence"].get("query_analysis")

    if isinstance(qa_dict, dict):
        status = qa_dict.get("status")
        reason = qa_dict.get("reason_l1")
        if status is not None:
            lines.append(f"query_analysis.status={status}")
        if reason is not None:
            lines.append(f"query_analysis.reason_l1={reason}")

    lines.append("")

    # -------------------------
    # 헬퍼: L1→L2 sentence 카드 렌더링
    # -------------------------
    def render_sentence_l1_to_l2(
        sent_block: dict,
        word_expls: list[dict] | None,
        include_word_core: bool = True,
        include_word_examples: bool = True,
        include_word_alternatives: bool = True,
        prefix: str = "",
    ):
        s = sent_block or {}
        # 1순위: 문장 번역
        lines.append(prefix + "L1→L2 SENTENCE BLOCK")
        lines.append(prefix + f"- l1_sentence: {s.get('l1_sentence')}")
        lines.append(prefix + f"- main_l2_sentence: {s.get('main_l2_sentence')}")

        # 2~3순위: 단어 해설
        if word_expls:
            lines.append(prefix + "- word_explanations:")
            for we in word_expls:
                # 2순위: 단어/의미/설명
                if include_word_core:
                    lines.append(prefix + f"    · l2_word: {we.get('l2_word')}")
                    lines.append(prefix + f"      meaning_l1: {we.get('meaning_l1')}")
                    if we.get("explanation_l1"):
                        lines.append(prefix + f"      explanation_l1: {we.get('explanation_l1')}")

                # 3순위: 예문
                if include_word_examples:
                    examples = we.get("examples") or []
                    if examples:
                        lines.append(prefix + "      examples:")
                        for ex in examples:
                            lines.append(prefix + f"        - src: {ex.get('source_sentence')}")
                            lines.append(prefix + f"          tgt: {ex.get('target_sentence')}")

                # 3순위: 대체 표현
                if include_word_alternatives:
                    alts_l2 = we.get("alternatives_l2") or []
                    if alts_l2:
                        lines.append(prefix + "      alternatives_l2:")
                        for alt in alts_l2:
                            lines.append(prefix + f"        - {alt}")

    # -------------------------
    # 헬퍼: L2→L1 sentence 카드 렌더링
    # -------------------------
    def render_sentence_l2_to_l1(
        sent_block: dict,
        word_expls: list[dict] | None,
        include_word_core: bool = True,
        include_word_examples: bool = True,
        include_word_alternatives: bool = True,
        prefix: str = "",
    ):
        s = sent_block or {}
        # 1순위: 문장 해석 + 문장 설명
        lines.append(prefix + "L2→L1 SENTENCE BLOCK")
        lines.append(prefix + f"- l2_sentence: {s.get('l2_sentence')}")
        lines.append(prefix + f"- main_l1_sentence: {s.get('main_l1_sentence')}")
        if s.get("sentence_explanation_l1"):
            lines.append(prefix + f"- sentence_explanation_l1: {s.get('sentence_explanation_l1')}")

        # 2~3순위: 단어 해설
        if word_expls:
            lines.append(prefix + "- word_explanations:")
            for we in word_expls:
                # 2순위: 단어/의미/설명
                if include_word_core:
                    lines.append(prefix + f"    · l2_word: {we.get('l2_word')}")
                    lines.append(prefix + f"      meaning_l1: {we.get('meaning_l1')}")
                    if we.get("explanation_l1"):
                        lines.append(prefix + f"      explanation_l1: {we.get('explanation_l1')}")

                # 3순위: 예문
                if include_word_examples:
                    examples = we.get("examples") or []
                    if examples:
                        lines.append(prefix + "      examples:")
                        for ex in examples:
                            lines.append(prefix + f"        - src: {ex.get('source_sentence')}")
                            lines.append(prefix + f"          tgt: {ex.get('target_sentence')}")

                # 3순위: 대체 표현
                if include_word_alternatives:
                    alts_l2 = we.get("alternatives_l2") or []
                    if alts_l2:
                        lines.append(prefix + "      alternatives_l2:")
                        for alt in alts_l2:
                            lines.append(prefix + f"        - {alt}")

    # ========================================
    # 1) DICTIONARY MODE
    # ========================================
    if mode_norm == "dict":

        # -----------------------------
        # 1-1) Word / Phrase
        # -----------------------------
        if qtype in ["word", "word_list", "phrase", "phrase_list"]:
            entries = data.get("entries") or []
            lines.append("[WORD/PHRASE ENTRIES]")

            for idx, ent in enumerate(entries):
                lines.append(f"- Entry #{idx+1}")
                lines.append(f"  source_text: {ent.get('source_text')}")
                lines.append(
                    f"  source_lang: {ent.get('source_lang')}, target_lang: {ent.get('target_lang')}"
                )

                variants = ent.get("variants") or []
                lines.append(f"  variants_count: {len(variants)}")

                for j, var in enumerate(variants):
                    lines.append(f"    - Variant #{j+1}")
                    # 1순위: target_text + explanation
                    lines.append(f"      target_text: {var.get('target_text')}")
                    if var.get("explanation"):
                        lines.append(f"      explanation: {var.get('explanation')}")

                    # 2순위: alternatives, 예문 1쌍
                    alt_list = var.get("alternatives") or []
                    if alt_list:
                        lines.append("      alternatives:")
                        for alt in alt_list:
                            lines.append(f"        - {alt}")

                    examples = var.get("examples") or []
                    if examples:
                        # 우선 1개만
                        first_ex = examples[0]
                        lines.append("      example:")
                        lines.append(f"        - src: {first_ex.get('source_sentence')}")
                        lines.append(f"          tgt: {first_ex.get('target_sentence')}")

                    # 3순위: 추가 예문 (있으면 뒤에 붙음 → 잘리기 쉬움)
                    extra_examples = (var.get("examples") or [])[1:]
                    if extra_examples:
                        lines.append("      extra_examples:")
                        for ex in extra_examples:
                            lines.append(f"        - src: {ex.get('source_sentence')}")
                            lines.append(f"          tgt: {ex.get('target_sentence')}")
                lines.append("")

        # -----------------------------
        # 1-2) Sentence (L1→L2 / L2→L1)
        # -----------------------------
        elif qtype == "sentence":
            lines.append("[SENTENCE MODE]")

            sent_block = data.get("sentence") or {}
            word_expls = data.get("word_explanations") or []

            # L1→L2
            if "l1_sentence" in sent_block:
                # 1순위 + 2순위 + 3순위 모두 넣되,
                # word_explanations 안에서 core → examples → alternatives 순서로 출력
                render_sentence_l1_to_l2(
                    sent_block,
                    word_expls,
                    include_word_core=True,
                    include_word_examples=True,
                    include_word_alternatives=True,
                )

                # 3순위: alternative_l2_sentences는 블록 끝에 추가
                alts = sent_block.get("alternative_l2_sentences") or []
                if alts:
                    lines.append("alternative_l2_sentences:")
                    for alt in alts:
                        lines.append(f"- {alt}")

            # L2→L1
            elif "l2_sentence" in sent_block and "main_l1_sentence" in sent_block:
                render_sentence_l2_to_l1(
                    sent_block,
                    word_expls,
                    include_word_core=True,
                    include_word_examples=True,
                    include_word_alternatives=True,
                )

            else:
                lines.append("Unknown sentence schema. RAW sentence block:")
                lines.append(str(sent_block))

            lines.append("")

        # -----------------------------
        # 1-3) Paragraph (L1→L2 / L2→L1)
        # -----------------------------
        else:
            lines.append("[PARAGRAPH MODE]")

            # ParagraphL1toL2Response
            if "l1_paragraph" in data:
                lines.append("Direction: L1 → L2 (ParagraphL1toL2Response)")
                # 1순위: 문단 전체 + 언어 정보
                lines.append("L1 paragraph:")
                lines.append(data.get("l1_paragraph") or "")
                lines.append(
                    f"l1_lang: {data.get('l1_lang')}, l2_lang: {data.get('l2_lang')}"
                )
                lines.append("")

                sentence_cards = data.get("sentence_cards") or []
                lines.append("Sentence cards (L1→L2):")

                for i, card in enumerate(sentence_cards):
                    lines.append(f"--- Sentence Card #{i+1} ---")
                    sent_block = (card or {}).get("sentence") or {}
                    we = (card or {}).get("word_explanations") or []

                    # 1순위: 문장 번역
                    # 2순위: word_explanations (core: word/meaning/explanation)
                    # 3순위: word_explanations의 examples/alternatives, alt sentences
                    render_sentence_l1_to_l2(
                        sent_block,
                        we,
                        include_word_core=True,
                        include_word_examples=True,
                        include_word_alternatives=True,
                        prefix="  ",
                    )

                    # 3순위: alternative_l2_sentences는 sentence 블록 끝에
                    alts = sent_block.get("alternative_l2_sentences") or []
                    if alts:
                        lines.append("  alternative_l2_sentences:")
                        for alt in alts:
                            lines.append(f"    - {alt}")

            # ParagraphL2toL1Response
            elif "l2_paragraph" in data:
                lines.append("Direction: L2 → L1 (ParagraphL2toL1Response)")
                # 1순위: 문단 전체, 통 번역, 문단 설명
                lines.append("L2 paragraph:")
                lines.append(data.get("l2_paragraph") or "")
                lines.append(
                    f"l2_lang: {data.get('l2_lang')}, l1_lang: {data.get('l1_lang')}"
                )
                lines.append("")
                lines.append("Paragraph-level translation and explanation:")
                lines.append(f"- paragraph_l1_translation: {data.get('paragraph_l1_translation')}")
                if data.get("paragraph_content_explanation_l1"):
                    lines.append(
                        f"- paragraph_content_explanation_l1: {data.get('paragraph_content_explanation_l1')}"
                    )

                lines.append("")
                lines.append("Sentence cards (L2→L1):")
                sentence_cards = data.get("sentence_cards") or []
                for i, card in enumerate(sentence_cards):
                    lines.append(f"--- Sentence Card #{i+1} ---")
                    sent_block = (card or {}).get("sentence") or {}
                    we = (card or {}).get("word_explanations") or []

                    # 1, 2, 3순위 순서대로 출력
                    render_sentence_l2_to_l1(
                        sent_block,
                        we,
                        include_word_core=True,
                        include_word_examples=True,
                        include_word_alternatives=True,
                        prefix="  ",
                    )

            else:
                lines.append("Unknown paragraph schema. RAW data:")
                lines.append(str(data))

    # ========================================
    # 2) ENCYCLOPEDIA MODE
    # ========================================
    else:
        lines.append("[ENCYCLOPEDIA ANSWER]")

        # 1순위: simplified_explanation + key_terms(term/definition)
        key_terms = data.get("key_terms") or []
        if key_terms:
            lines.append("key_terms:")
            for kt in key_terms:
                lines.append(f"- term: {kt.get('term')}")
                lines.append(f"  definition: {kt.get('definition')}")

        lines.append("")
        lines.append("simplified_explanation:")
        lines.append(data.get("simplified_explanation") or "")

        # 2순위: input_text, usage_context
        if data.get("input_text"):
            lines.append("")
            lines.append("input_text:")
            lines.append(data.get("input_text") or "")

        if data.get("usage_context"):
            lines.append("")
            lines.append("usage_context:")
            lines.append(data.get("usage_context") or "")

        # 3순위: analogy, extra_notes
        if key_terms:
            any_analogy = any(kt.get("analogy") for kt in key_terms)
            if any_analogy:
                lines.append("")
                lines.append("key_term_analogies:")
                for kt in key_terms:
                    if kt.get("analogy"):
                        lines.append(f"- term: {kt.get('term')}")
                        lines.append(f"  analogy: {kt.get('analogy')}")

        if data.get("extra_notes"):
            lines.append("")
            lines.append("extra_notes:")
            lines.append(data.get("extra_notes") or "")

    # ========================================
    # 길이 하드 컷 (뒤쪽부터 잘리도록)
    # ========================================
    verifier_text = "\n".join(lines)
    MAX_CHARS = 4000
    if len(verifier_text) > MAX_CHARS:
        verifier_text = verifier_text[:MAX_CHARS] + "\n... [TRUNCATED FOR VERIFIER]"

    return verifier_text

def build_regeneration_instruction(feedback_comment: str, field: str, mode: str) -> str:
    """
    Create a strict regeneration instruction based on Verifier feedback.
    Policy:
    - If mode='dict' and field is a specific domain (not 'general'),
        ONLY that domain's senses must appear.
    - If mode='dict' and field is 'general' or empty,
        the answer should focus on general / most common senses,
        not narrow technical meanings unless clearly asked.
    This instruction is appended after the generator prompt and never shown to users.
    """

    base_header = (
        "\n\n"
        "You must regenerate a NEW answer for the same user query, fully obeying the following rules:\n"
        "1) You MUST fix ALL issues identified by the internal verifier.\n"
        "2) You MUST NOT repeat any mistaken senses, alternatives, or examples.\n"
    )

    field = (field or "").strip().lower()

    field_block = ""
    # dict + specific field → field-exclusive
    if mode == "dict" and field and field != "general":
        field_block = (
            f"3) The dictionary mode is FIELD-EXCLUSIVE. The field is '{field}'.\n"
            f"   -> You MUST output ONLY meanings, explanations, examples, and alternatives belonging to the '{field}' domain.\n"
            f"   -> ANY general or out-of-field sense MUST be removed.\n"
            f"   -> Example: if field='finance', general meanings like 'interest = curiosity' MUST NOT appear.\n"
        )
    # dict + general → 일반적 의미 우선
    elif mode == "dict" and (not field or field == "general"):
        field_block = (
            "3) The dictionary mode is in GENERAL field.\n"
            "   -> You MUST focus on the general, most common everyday senses of the query.\n"
            "   -> You MUST NOT restrict the meaning to a narrow technical sub-domain\n"
            "      (e.g., do not focus only on finance, law, or medicine unless the query itself clearly demands it).\n"
        )

    if not feedback_comment:
        # No explicit comment → use strict default regeneration
        return (
            base_header +
            field_block +
            "4) Regenerate the answer cleanly and concisely.\n"
            "5) Do NOT add unnecessary information.\n"
            "6) The JSON structure of the answer MUST follow the original schema.\n"
        )

    # Feedback-aware version
    return (
        base_header +
        field_block +
        "4) The internal verifier found the following issue(s):\n"
        f"   {feedback_comment}\n\n"
        "5) You MUST explicitly correct the above issues.\n"
        "6) You MUST NOT reintroduce the same incorrect senses, examples, or alternatives.\n"
        "7) Do NOT add irrelevant or unnecessary information.\n"
        "8) The final output MUST strictly match the original required JSON schema.\n"
    )
    
# (1130 02:41) 만휘 수정.
# 현재 Verifier가 Sentence의 query_analysis.status 결과를 제대로 못 봄
# 그래서 볼 수 있도록 '임시 수정'
# 왜 못보냐면, 기존 애들은 query_analysis.status 에 결과가 들어있는데,
# sentence query는 sentence.query_analysis.status 에 들어있음.
# 왜 여기 들어있는지는 아직 못 봤지만, 암튼 일단 급하게 수정.
# 추후 제대로 수정 필요할 듯.
def _extract_query_analysis_status(entry: Any) -> Optional[str]:
    """
    LLM 응답(entry)에서 query_analysis.status를 최대한 안전하게 뽑는다.
    - Word/Paragraph/Encyclopedia: 최상위에 query_analysis가 있음
    - SentenceL1/L2: sentence.query_analysis 안에만 있음
    """
    try:
        data = entry.model_dump()
    except Exception:
        data = entry

    if not isinstance(data, dict):
        return None

    qa_dict = None

    # 1) 최상위에 있는 경우 (WordDictResponse, ParagraphL*toL*Response, EncyclopediaResponse 등)
    if "query_analysis" in data:
        qa_dict = data.get("query_analysis")

    # 2) sentence 블록 안에만 있는 경우 (SentenceL1toL2Response / SentenceL2toL1Response)
    elif isinstance(data.get("sentence"), dict) and "query_analysis" in data["sentence"]:
        qa_dict = data["sentence"].get("query_analysis")

    if isinstance(qa_dict, dict):
        status = qa_dict.get("status")
        if isinstance(status, str):
            return status

    return None



# ----------------------------
# 4. /api/search
# ----------------------------

@app.route("/api/search", methods=["POST"])
def api_search():
    try:
        data = request.get_json() or {}

        query = (data.get("query") or "").strip()
        education = (data.get("education") or "").strip()
        field = (data.get("field") or "").strip() or "general"
        mode = (data.get("mode") or "dict").strip()

        # native_lang : 모국어 / target_lang : 타국어 (사용자가 배우고 싶은 언어)
        native_lang: LangCode = (data.get("native_lang") or "ko").strip()
        target_lang: LangCode = (data.get("target_lang") or "en").strip()

        if not query:
            return jsonify({"error": "Query is empty."}), 400

        # ✅ LLM 모델 선택
        #   - education 코드는 prompt_rule.py의 _education_label과 맞춰서 사용
        #   - 예: "elementary", "middle", "high", "bachelor", "master", "doctor"
        llm = (
            "models/gemini-2.5-flash"
            if education in ["master", "doctor"]
            else "models/gemini-2.5-flash-lite"
        )

        # A-1: Query Analyzer
        analysis = analyze_query(
            query=query,
            native_lang=native_lang,
            target_lang=target_lang,
        )

        # 디버깅용 출력 (원하면 끄거나 줄여도 됨)
        print("\n===== [A-1 Query Analysis] =====")
        print("raw_query    :", analysis.raw_query)
        print("normalized   :", analysis.normalized_query)
        print("query_type   :", analysis.query_type)
        print("units        :", analysis.units)
        print("query_lang   :", analysis.query_lang)
        print("================================\n")

        # 스키마 선택 (generator 전용)
        generator_schema = select_schema(mode, analysis, native_lang)

        generator_config = {
            "response_schema": generator_schema,
            "response_mime_type": "application/json",
            "max_output_tokens": 65536,
        }

        # A-2: Rule-based Prompt Composer
        generator_prompt = generate_prompt_rule(
            analysis=analysis,
            education=education,
            field=field,
            mode=mode,
            native_lang=native_lang,
            target_lang=target_lang,
        )

        print("===== [A-2 Prompt] =====")
        # print(generator_prompt)

        print(f"Using model: {llm}")
        print(f"Mode       : {mode}")
        print(f"Schema     : {generator_schema.__name__}")
        print("=========================\n")

        # ----------------------------
        # B-1: Gemini 호출 (1차 생성)
        # ----------------------------
        generator_response = client.models.generate_content(
            model=llm,
            contents=generator_prompt,
            config=generator_config,
        )

        entry = generator_response.parsed  # Pydantic 모델 인스턴스
        if entry is None:
            # 혹시 parsed가 비어있으면, raw JSON 텍스트를 스키마로 파싱
            raw_text = getattr(generator_response, "text", "")
            entry = generator_config["response_schema"].model_validate_json(raw_text)

        print("===== [Model Parsed Output - First Pass] =====")
        print(entry.model_dump())
        print("==============================================\n")

        # ----------------------------
        # C: Verifier + (필요 시) 재생성
        # ----------------------------


        # (1130 02:41) 만휘 수정.
        # 현재 Verifier가 Sentence의 query_analysis.status 결과를 제대로 못 봄
        # 그래서 볼 수 있도록 '임시 수정'
        # 왜 못보냐면, 기존 애들은 query_analysis.status 에 결과가 들어있는데,
        # sentence query는 sentence.query_analysis.status 에 들어있음.
        # 왜 여기 들어있는지는 아직 못 봤지만, 암튼 일단 급하게 수정.
        # 추후 제대로 수정 필요할 듯.
        # 1) query_analysis.status가 VALID가 아닐 경우:
        #    - 어차피 본문 생성이 아니라 안내 메시지 위주이므로
        #      Verifier를 돌릴 필요 없이 그대로 반환한다.
        #
        #    Sentence 응답에서는 query_analysis가 sentence 블록 안에만 있을 수 있으므로
        #    헬퍼로 안전하게 status를 추출한다.
        qa_status_value = _extract_query_analysis_status(entry)

        if qa_status_value != "VALID":
            # Verifier 패스, 곧바로 반환
            return jsonify(entry.model_dump())


        # 2) VALID인 경우에만 Verifier를 태운다.
        #
        #    ⚠️ 여기서 중요한 점:
        #    - mode, query_type, query_lang, native_lang, target_lang을 이용해
        #      "실제 사전 방향"에 맞는 언어 정보를 Verifier에 넘겨야 한다.
        #
        #    - L1 = native_lang (사용자의 모국어, 설명/해설 기본 언어)
        #    - L2 = target_lang (사용자가 배우고 싶은 언어)
        #
        #    - L1 → L2 사전: query_lang == L1
        #    - L2 → L1 사전: query_lang == L2
        #
        L1 = native_lang
        L2 = target_lang

        if mode == "dict":
            if analysis.query_type in ["word", "word_list", "phrase", "phrase_list", "sentence", "paragraph"]:
                if analysis.query_lang == L1:
                    # L1 → L2 방향 (예: ko → en)
                    verifier_source_lang = L1
                    verifier_target_lang = L2
                else:
                    # L2 → L1 방향 (예: en → ko)
                    # 쿼리는 L2로 들어오고, 설명/번역은 L1로 나가는 것이 정상.
                    verifier_source_lang = analysis.query_lang  # 보통 L2
                    verifier_target_lang = L1
            else:
                # 혹시 정의되지 않은 타입이 들어오면 보수적으로 처리
                verifier_source_lang = analysis.query_lang
                verifier_target_lang = None
        else:
            # encyclopedia: 사실상 단일 언어 설명
            verifier_source_lang = analysis.query_lang
            verifier_target_lang = None

        # Verifier에 넘길 answer_text를 모드/쿼리 타입별로 요약
        verifier_answer_text = build_verifier_answer_text(
            entry=entry,
            mode=mode,
            query_type=analysis.query_type,
        )

        verifier_result: VerifierResult = run_verifier(
            query_text=query,
            mode=mode,
            query_type=analysis.query_type,
            # 전체 구조를 문자열로 넘김 (나중에 필요하면 의미 텍스트만 추출하도록 개선 가능)
            answer_text=verifier_answer_text,
            field=field,
            source_lang=verifier_source_lang,
            target_lang=verifier_target_lang,
        )

        print("===== [Verifier Result] =====")
        print(verifier_result.model_dump())
        print("=============================\n")

        # 3) threshold 기준으로 재생성 여부 결정
        if not verifier_result.needs_regeneration(VERIFIER_HALLUCINATION_THRESHOLD):
            # 안전하다고 판단 → 1차 답변 그대로 유저에게 반환
            return jsonify(entry.model_dump())

        # 4) 재생성 필요 → Verifier comment를 활용해 Main LLM 재호출
        regen_instruction = build_regeneration_instruction(
            feedback_comment=verifier_result.comment,
            field=field,
            mode=mode,
        )

        # 기존 generator_prompt에 재생성 지시문을 추가
        regen_prompt = generator_prompt + regen_instruction
        

        print("===== [Regeneration Prompt] =====")
        print(regen_prompt)
        print("=================================\n")

        regen_response = client.models.generate_content(
            model=llm,
            contents=regen_prompt,
            config=generator_config,
        )

        entry_regen = regen_response.parsed
        if entry_regen is None:
            raw_text_regen = getattr(regen_response, "text", "")
            entry_regen = generator_config["response_schema"].model_validate_json(raw_text_regen)

        print("===== [Model Parsed Output - Regenerated] =====")
        print(entry_regen.model_dump())
        print("===============================================\n")

        # 재생성된 결과를 최종적으로 반환
        return jsonify(entry_regen.model_dump())

    except Exception as e:
        print("❌ [ERROR] Exception occurred in /api/search")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 5. 서버 실행
# ----------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=True)
