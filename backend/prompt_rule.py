# prompt_rule.py
"""
Prompt Adaptation Layer - Rule-based 버전 (A-2)

- A-1(Query Analyzer)의 결과 + 유저 프로필을 받아
- 최종적으로 Gemini에 넘길 영어 프롬프트 문자열을 만든다.
- 여기서는 LLM 기반 meta-prompt는 전혀 쓰지 않는다.
"""

from __future__ import annotations
from typing import Literal

from utils.query_analyzer import (
    QueryAnalysisResult,
    LangCode,   # Literal["ko", "en", "zh", "de"]
    QueryType,  # Literal["word", "word_list", "phrase", "phrase_list", "sentence", "paragraph"]
)


Mode = Literal["dict", "dictionary", "encyclopedia"]


def _normalize_mode(mode: str) -> Mode:
    m = (mode or "").strip().lower()
    if m in ("dict", "dictionary"):
        return "dict"
    return "encyclopedia"


def _direction(query_lang: LangCode, native_lang: LangCode, target_lang: LangCode) -> str:
    """
    native_lang / target_lang 두 개 중 쿼리가 어느 쪽인지에 따라 방향 결정.
    """
    if query_lang == native_lang:
        return "native_to_target"
    elif query_lang == target_lang:
        return "target_to_native"
    # 이론상 오면 안 되는데, 안전빵으로:
    return "native_to_target"


def _join_units(units) -> str:
    """
    분석된 units 리스트를 LLM에 보여줄 human-readable 텍스트로 합치기.
    """
    if not units:
        return ""
    if len(units) == 1:
        return units[0]
    # 리스트는 번호 매겨서 정리
    lines = []
    for i, u in enumerate(units, 1):
        lines.append(f"{i}. {u}")
    return "\n".join(lines)


def _education_label(education: str) -> str:
    """
    index.html에서 온 education 코드값을 LLM 프롬프트에서 사용할
    영어 라벨로 변환한다.
    """
    e = (education or "").strip().lower()

    mapping = {
        "elementary": "elementary school student",
        "middle": "middle school student",
        "high": "high school student",
        "bachelor": "undergraduate student",
        "master": "master's student",
        "doctor": "doctoral-level learner",
    }
    # 기본값
    return mapping.get(e, "intermediate adult learner")


def _level_guidance(education: str) -> str:
    """
    Condensed level guidance for LLM output.
    Technical terms must NEVER be replaced or paraphrased at any level.
    """
    e = (education or "").strip().lower()

    if e == "elementary":
        # ★ UPDATED: 도메인 기술 용어도 허용하되, 아주 쉽게 설명하도록 명시
        return (
            "Level: Elementary\n"
            "- Technical terms: keep exact; add very short plain definition.\n"
            "- Lexical: basic daily words; technical terms from the user's field are allowed but must be explained in very simple language.\n"
            "- Syntax: very short simple sentences; no subordinate clauses.\n"
            "- Explanation: direct, concrete, minimal detail. Use friendly and clear emojis frequently to support understanding (about 1 emoji per clause is okay).\n"
            "- Abstraction: fully concrete; no invisible mechanisms.\n"
            "- Examples: everyday context plus very simple field-related examples; 1-sentence examples.\n"
        )
    
    if e == "middle":
        return (
            "Level: Middle School\n"
            "- Technical terms: unchanged; brief intuitive explanation.\n"
            "- Lexical: common words; basic academic vocab with clarification.\n"
            "- Syntax: simple compound sentences; basic connectors.\n"
            "- Explanation: idea → reason → short analogy/example.\n"
            "- Abstraction: light cause–effect reasoning.\n"
            "- Examples: simple academic contexts; 1–2 sentence scenarios.\n"
            "- Style: use emojis sparingly (e.g., 1 per 2–3 sentences) only when they help emphasize or clarify meaning.\n"
        )

    if e == "high":
        return (
            "Level: High School\n"
            "- Technical terms: unchanged; clarify when needed.\n"
            "- Lexical: basic academic vocab allowed.\n"
            "- Syntax: clear compound/complex sentences (1–2 ideas each).\n"
            "- Explanation: intuition → mechanism → limitation.\n"
            "- Abstraction: medium-level; simplified models/processes.\n"
            "- Examples: real-world + academic mix; 2–3 sentence cases.\n"
        )

    if e == "bachelor":
        return (
            "Level: Bachelor\n"
            "- Technical terms: used freely and precisely.\n"
            "- Lexical: semi-specialized terms; define only if useful.\n"
            "- Syntax: complex sentences; avoid heavy nesting.\n"
            "- Explanation: concept → properties → concise example.\n"
            "- Abstraction: medium–high; brief theory framing.\n"
            "- Examples: empirical or policy-related.\n"
        )

    if e == "master":
        return (
            "Level: Master\n"
            "- Technical terms: fully used; define only unfamiliar items.\n"
            "- Lexical: domain terminology encouraged.\n"
            "- Syntax: academic structures; higher information density.\n"
            "- Explanation: assumption → mechanism → implication.\n"
            "- Abstraction: high-level; models and causal reasoning.\n"
            "- Examples: simplified research-oriented cases.\n"
        )

    if e == "doctor":
        return (
            "Level: Doctoral\n"
            "- Technical terms: exact and precise; fine distinctions.\n"
            "- Lexical: unrestricted domain-theoretical vocabulary.\n"
            "- Syntax: advanced academic structures; inference chains.\n"
            "- Explanation: compressed, mechanism-centered; alternatives allowed.\n"
            "- Abstraction: very high; model-level and theoretical logic.\n"
            "- Examples: research-level cases (trade-offs, identification issues).\n"
        )

    # Fallback
    return (
        "Level: Intermediate Adult\n"
        "- Technical terms unchanged.\n"
        "- Clear vocabulary; moderate complexity.\n"
        "- Balanced explanations with brief definitions.\n"
        "- Moderate abstraction.\n"
        "- Everyday + academic examples.\n"
    )



# ----------------------------------------------------------------------
#   메인 함수: generate_prompt_rule
# ----------------------------------------------------------------------

def generate_prompt_rule(
    analysis: QueryAnalysisResult,
    *,
    education: str,   # 코드값: "elementary" / "middle" / "high" / "bachelor" / "master" / "doctor"
    field: str,
    mode: str,
    native_lang: LangCode,
    target_lang: LangCode,
) -> str:
    """
    Rule-based Prompt Composer (A-2)

    Parameters
    ----------
    analysis : QueryAnalysisResult
        A-1 Query Analyzer 결과.
    education : str
        index.html에서 넘어오는 레벨 코드값
        ("elementary", "middle", "high", "bachelor", "master", "doctor")
    field : str
        전공/공부 분야 (예: "컴퓨터공학", "언어학", "경영학")
    mode : str
        "dict" / "dictionary" / "encyclopedia"
    native_lang : LangCode
    target_lang : LangCode

    Returns
    -------
    prompt : str
        Gemini에 바로 넣을 영어 프롬프트 문자열.
    """
    m = _normalize_mode(mode)
    qtype: QueryType = analysis.query_type
    units = analysis.units
    query_lang: LangCode = analysis.query_lang or native_lang

    direction = _direction(query_lang, native_lang, target_lang)
    is_list = qtype in ("word_list", "phrase_list", "paragraph")
    is_lexical = qtype in ("word", "word_list", "phrase", "phrase_list")

    units_block = _join_units(units)

    # 레벨 관련 정보
    edu_label = _education_label(education)
    level_block = _level_guidance(education)

    # ✅ field 정규화
    field_norm = (field or "").strip().lower()

    # ✅ 모드/field에 따른 도메인 행동 규칙
    if m == "dict":
        if not field_norm or field_norm == "general":
            domain_block = f"""[Domain behavior for dictionary mode]

In dictionary mode with a GENERAL field:

- You MUST focus on the general, most common everyday senses of the query.
- You MUST NOT restrict the meaning to a narrow technical sub-domain
  unless the query text itself clearly demands it (e.g., contains explicit technical notation or jargon).
- If a word also has specialized technical meanings in particular fields,
  you may briefly mention them only after the general sense, and only if they are clearly helpful for the user.

These rules OVERRIDE any later generic domain hints in this prompt whenever they conflict.
"""
        else:
            domain_block = f"""[Domain behavior for dictionary mode]

In dictionary mode with a SPECIFIC field:

- The field is '{field}' and dictionary mode is FIELD-EXCLUSIVE.
- You MUST ONLY output senses, translations, explanations, examples, and alternatives
  that belong to the '{field}' domain.
- You MUST NOT mention general or out-of-field senses, even as secondary background.
- For example, if field = "finance" and the query is "interest",
  you MUST only output the financial sense (e.g., '이자') and MUST NOT mention
  the general '관심/흥미' sense.

These rules OVERRIDE any later generic domain hints in this prompt whenever they conflict.
"""
    else:
        domain_block = f"""[Domain behavior for encyclopedia mode]

In encyclopedia mode:

- The field '{field}' describes the user's study area.
- When multiple interpretations exist, you should prioritize explanations,
  examples, and analogies that are relevant to this field.
- However, you may still mention general meanings or cross-domain background
  when it helps understanding.
"""

    # ---------------------------------------------------
    # 공통 헤더: 시스템 역할 + structured output + Query Validation
    # ---------------------------------------------------

    header = f"""
You are the core reasoning engine of a multi-lingual learning dictionary called "AdapDict".

If query_analysis.status != "VALID", you MUST ignore all mode-specific instructions below and leave non-query_analysis fields empty.

- User native language (L1): {native_lang}
- User target language (L2): {target_lang}
- User education level: {edu_label} (code: {education})
- User field of study: {field}
- Query type: {qtype}
- Mode: {"dictionary" if m == "dict" else "encyclopedia"}

You MUST strictly follow the server-side JSON schema given via the API (response_schema).
Do NOT invent new fields or change the schema structure.
The API will parse your output directly into a typed schema, so you must stay consistent.

[User level adaptation guidelines]
{level_block}

{domain_block}
[STEP 0: Query validation and query_analysis]

Before generating any dictionary or encyclopedia content, you MUST first evaluate whether the user's query itself is valid for this system.

You MUST always fill the top-level field "query_analysis" in the JSON response with the following structure:

- query_analysis.status: one of
  - "VALID"
  - "TYPO"
  - "FACTUAL_ERROR"
  - "AMBIGUOUS"
  - "NONSENSE"
- query_analysis.reason_l1:
  a short, user-facing explanation written in the user's native language L1 ({native_lang}).
- query_analysis.suggestion_queries:
  a list of 0–3 alternative query strings (or null) when appropriate.

Use the statuses as follows:

1) "VALID":
  - The query is a reasonable input for this mode and query type.
  - Example: a normal word, phrase, sentence, or paragraph that is meaningful.
  - In this case:
    - Set query_analysis.reason_l1 to a very short confirmation in L1 ({native_lang}),
      e.g. "정상적인 쿼리입니다." (if L1 is Korean) or a similar short message in L1.
    - You MUST then generate ALL other fields in the schema normally
      (dictionary/encyclopedia content) according to the mode-specific instructions below.

2) "TYPO":
  - The query contains a spelling mistake, malformed word, or non-existent lexical item that is very close to known words.
  - Example: "applr" (likely "apple" or "apply").
  - In this case:
    - query_analysis.reason_l1:
      explain in L1 ({native_lang}) what seems wrong and which real words it may correspond to.
      or example, if L1 is Korean:
      "입력하신 'applr'는 알려진 영어 단어가 아니며, 'apple' 또는 'apply'의 오타일 가능성이 높습니다."
    - query_analysis.suggestion_queries:
      include 1–3 likely intended queries, e.g. ["apple", "apply"].
    - For ALL other fields in the schema (dictionary/encyclopedia content),
      you MUST NOT generate a full answer.
      Instead, keep them empty or minimal (empty strings, empty lists, or null),
      because the user needs to re-enter or correct the query.

3) "FACTUAL_ERROR":
  - The query is a sentence or paragraph whose content is clearly false
    with respect to widely known facts.
  - Example: "지구는 네모다.", "서울은 일본의 수도이다."
  - In this case:
    - query_analysis.reason_l1:
      clearly state in L1 ({native_lang}) that the sentence is factually wrong and briefly provide the correct fact.
      For example, in Korean:
      "입력하신 문장은 사실과 다릅니다. 지구는 네모가 아니라 둥근 타원체에 가깝습니다."
    - query_analysis.suggestion_queries: usually null.
    - You MUST NOT build a full dictionary/encyclopedia explanation
      treating the false statement as if it were true.
      Instead, only give minimal or empty values for the other fields,
      and focus on correcting the misunderstanding via query_analysis.reason_l1.

4) "AMBIGUOUS":
  - The query is too vague, incomplete, or underspecified to know what the user really wants.
  - Example: a single letter, a very short fragment, or an extremely broad word with no context.
  - In this case:
    - query_analysis.reason_l1:
      explain in L1 ({native_lang}) why the query is ambiguous or incomplete.
    - Suggest in L1 how the user could rewrite the query more specifically
      (e.g., add more words, specify field or sentence).
    - query_analysis.suggestion_queries:
      you may propose 1–3 more precise example queries.
    - DO NOT generate a full dictionary/encyclopedia answer;
      keep other fields minimal or empty.

5) "NONSENSE":
  - The query is structurally or semantically nonsensical
    so that no meaningful interpretation can be made.
  - Example: random characters, words in a sequence that do not form a coherent sentence or concept,
    or logically contradictory gibberish.
  - In this case:
    - query_analysis.reason_l1:
      briefly explain in L1 ({native_lang}) why the input is not understandable.
    - query_analysis.suggestion_queries:
      usually null, unless you can suggest a clear, sensible alternative.
    - DO NOT generate a full dictionary/encyclopedia answer;
      keep other fields minimal or empty.

[IMPORTANT]

- You MUST always fill query_analysis first.
- If query_analysis.status != "VALID":
  - You MUST NOT generate a normal dictionary/encyclopedia answer.
  - All other fields in the schema should be left empty or minimal.
  - The user interface will show query_analysis.reason_l1 as the main message to the user.
- Only when query_analysis.status == "VALID" are you allowed to fully populate
  the remaining fields in the schema according to the mode-specific instructions below.
"""

    # ---------------------------------------------------
    # 모드별 / 방향별 세부 지침
    # ---------------------------------------------------

    if m == "encyclopedia":
        # ==============================
        #   Encyclopedia mode
        #   - 항상 native_lang(L1)로 설명
        #   - target_lang(L2)는 있어도 예시 정도
        # ==============================
        body = f"""
[Task: Encyclopedia-style explanation]

The user has asked about the following content:

--- QUERY UNITS ---
{units_block}
-------------------

Your job:

1. Treat the input as a concept or a set of related concepts.
2. Explain everything in L1 ({native_lang}) only.
3. Adjust difficulty to the user's education level ({edu_label})
  and field of study ({field}). Use field-appropriate analogies if helpful.
4. Clearly break down:
  - What it is
  - Why it matters
  - Where it is commonly used or seen (usage context)
  - Any intuitive examples or analogies
5. If there are multiple units (list or paragraph), you may:
  - either focus on the central overarching concept, OR
  - briefly cover each unit, grouped logically,
  depending on what makes more sense for understanding.
6. If the concept has a specialized meaning in the user's field ({field}),
  you MUST prioritize that field-specific explanation first, and then optionally
  mention general meanings later as background.

Remember:
- Output must be fully in L1 ({native_lang}).
- Follow the structured fields in the EncyclopediaResponse schema
  (e.g., input_text, key_terms, simplified_explanation, usage_context, extra_notes, ...).
"""

        return header + body

    # =========================================================
    #   Dictionary mode (m == "dict")
    #   방향: native_to_target / target_to_native
    # =========================================================

    # 1) native_lang → target_lang (사용자가 모국어로 질문)
    if direction == "native_to_target":
        if is_lexical:
            # -----------------------
            #   단어 / 구 / 리스트
            # -----------------------
            if is_list:
                body = f"""
[Task: Bilingual dictionary for multiple lexical items]

The user entered L1 ({native_lang}) lexical items (words/phrases).
You receive a list of items and must produce a dictionary-style entry
for EACH item in the list.

--- L1 ITEMS ---
{units_block}
----------------

For EACH item:

1. First, check whether this item is used as a technical term in the user's field ({field}).
  - If a field-specific sense exists, you MUST follow the domain behavior described above
    in the [Domain behavior for dictionary mode] block.
2. Identify the most natural L2 ({target_lang}) translation or expression for the primary sense.
3. Provide several alternative L2 expressions with similar meaning
  when relevant (e.g., synonyms, more formal/informal variants).
4. Provide 1~3 example sentences in L2 for that item,
  adjusted to the user's level ({education}) and field ({field}).
5. Add explanations in L1 ({native_lang}) that:
  - clarify nuance or typical usage,
  - give simple analogies or concrete situations,
  - highlight any important domain-specific aspects if relevant.

All explanations and meta-explanations must be in L1 ({native_lang}).
All example sentences and lexical realizations must be in L2 ({target_lang}).

Return one dictionary entry per item, following the AdapDictResponse schema.
"""
            else:
                # word / phrase (단일)
                body = f"""
[Task: Bilingual dictionary for a single lexical item]

The user entered one lexical item in L1 ({native_lang}).

--- L1 QUERY ---
{units_block}
---------------

Your job:

1. Detect whether this item has relevant general or field-specific senses,
  and then follow the domain behavior defined in the [Domain behavior for dictionary mode] block.
2. Give the most natural L2 ({target_lang}) translation or expression for the primary sense.
3. Provide several alternative L2 expressions with similar meaning
  (synonyms, more casual/formal variants, domain-specific alternatives).
4. Provide 2~4 example sentences in L2 that:
  - match the user's level ({education}),
  - reflect the user's field of study ({field}) when appropriate.
5. Explain in L1 ({native_lang}):
  - nuance and typical usage,
  - any register or politeness constraints,
  - common collocations or typical patterns.

Explanations must be in L1.
Translations and examples must be in L2.
Follow the AdapDictResponse schema exactly.
"""
        else:
            # -----------------------
            #   문장 / 문단
            # -----------------------
            if is_list:  # paragraph → 문장들 리스트
                body = f"""
[Task: Sentence-level translation and explanation for multiple sentences]

The user wrote a paragraph in L1 ({native_lang}).
You receive it segmented into sentences:

--- L1 SENTENCES ---
{units_block}
--------------------

For EACH sentence:

1. Produce a natural L2 ({target_lang}) translation,
  as if you are doing careful writing/translation for a learner.
2. If any key words/phrases in the sentence have specialized meanings in the user's field ({field}),
  you MUST preserve and clarify those domain-specific meanings when required by the [Domain behavior] block.
3. Optionally suggest 1~2 alternative L2 rewrites that:
  - sound more natural,
  - or fit slightly different registers (formal/casual),
  matching the user's level ({education}) and field ({field}).
4. Provide short L1 ({native_lang}) explanations when needed
  (e.g., why a certain structure was chosen).

All explanations are in L1.
All translations and alternative rewrites are in L2.

Use the sentence-level schema (SenseSentenceResponse) if configured,
or otherwise a multi-entry dictionary schema.
"""
            else:
                # sentence (단일)
                body = f"""
[Task: Sentence translation and enhancement]

The user wrote a single sentence in L1 ({native_lang}).

--- L1 SENTENCE ---
{units_block}
-------------------

Your job:

1. Translate the sentence into natural L2 ({target_lang}),
  matching the user's level ({education}) and field ({field}).
2. If any key terms in the sentence are used in a field-specific way ({field}),
  you MUST preserve and clarify that domain-specific meaning in your translation,
  consistent with the [Domain behavior for dictionary mode].
3. Provide 1~3 alternative L2 rewrites:
  - one slightly more formal,
  - one slightly more casual or conversational,
  - optionally one that is more domain-specific if {field} suggests it.
4. In L1 ({native_lang}), briefly explain:
  - key grammar or expression choices,
  - any important nuances or possible pitfalls,
  - especially how field-specific meanings are reflected in L2.

Explanations must be in L1.
Translations and alternative sentences must be in L2.
Follow the sentence schema (SenseSentenceResponse) when it is used.
"""

        return header + body

    # 2) target_lang → native_lang (사용자가 공부 언어로 질문)
    else:  # direction == "target_to_native"
        if is_lexical:
            if is_list:
                body = f"""
[Task: Understanding-focused dictionary for multiple L2 lexical items]

The user entered several lexical items in L2 ({target_lang}).

--- L2 ITEMS ---
{units_block}
----------------

For EACH item:

1. Detect whether this item has general and/or specialized meanings,
  and then follow the domain behavior defined in the [Domain behavior for dictionary mode] block.
2. Provide an accurate L1 ({native_lang}) translation or explanation
  for the primary sense.
3. Explain in L1:
  - nuance, register (formal/informal), and common usage,
  - differences from near-synonyms,
  - typical collocations or patterns.
4. Provide 1~2 example sentences in L2 ({target_lang}) for each item,
  adjusted to the user's level ({education}) and field ({field}).
5. Optionally suggest a few related L2 expressions or useful phrases,
  but keep the focus on understanding the original items.

All explanations must be in L1.
Examples and lexical realizations are in L2.
Return one dictionary entry per item using the AdapDictResponse schema.
"""
            else:
                body = f"""
[Task: Understanding-focused dictionary for a single L2 lexical item]

The user entered one lexical item in L2 ({target_lang}).

--- L2 QUERY ---
{units_block}
---------------

Your job:

1. Determine whether this lexical item has general and/or field-specific senses,
  and apply the rules from the [Domain behavior for dictionary mode] block.
2. Provide an L1 ({native_lang}) translation or concise paraphrase
  for the primary sense, tuned to the user's level ({education}) and field ({field}).
3. In L1, explain:
  - nuance and typical usage,
  - common collocations,
  - differences from similar words.
4. Provide 2~3 example sentences in L2 ({target_lang}) that illustrate usage,
  preferably in contexts related to {field} when appropriate.
5. Optionally propose a few alternative L2 expressions, but keep the focus
  on understanding the original item.

All explanations are in L1.
Examples and lexical forms are in L2.
Follow the AdapDictResponse schema exactly.
"""
        else:
            # 문장 / 문단
            if is_list:
                body = f"""
[Task: Comprehension and explanation for multiple L2 sentences]

The user wrote a paragraph in L2 ({target_lang}).
You receive it segmented into sentences:

--- L2 SENTENCES ---
{units_block}
--------------------

For EACH sentence:

1. Provide an L1 ({native_lang}) translation that is natural and clear.
2. In L1, briefly explain:
  - important grammar points,
  - idiomatic expressions or tricky parts,
  - any field-specific terms relevant to {field}, consistent with the [Domain behavior] block.
3. Optionally suggest 1~2 improved L2 versions of each sentence
  (more natural, clearer, or better suited for the user's level {education}),
  keeping field-specific meanings accurate when required.

All meta-explanations must be in L1.
Translations and improved versions are in L1 (translation) + L2 (improved).
Use the sentence schema (SenseSentenceResponse) if configured.
"""
            else:
                body = f"""
[Task: Comprehension and refinement for a single L2 sentence]

The user entered one sentence in L2 ({target_lang}).

--- L2 SENTENCE ---
{units_block}
-------------------

Your job:

1. Translate the sentence into L1 ({native_lang}) in a way that:
  - is easy to understand at the user's level ({education}),
  - correctly reflects any field-specific meanings in {field}
    according to the [Domain behavior for dictionary mode] block.
2. In L1, explain:
  - grammar or structure,
  - nuance of key phrases,
  - any common mistakes or pitfalls learners make with this pattern,
  - especially clarifying the domain-specific sense if there is both a general and field-specific meaning.
3. Provide 1~2 improved or alternative L2 versions
  (e.g., more natural, more polite, or more context-appropriate),
  while preserving the correct sense as required by the domain rules.

All explanations are in L1.
Only the improved versions are in L2.
Follow the sentence-level schema where applicable.
"""

        return header + body
