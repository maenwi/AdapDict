# schemas/encyclopedia.py

from pydantic import BaseModel
from typing import List, Optional
from .common import QueryAnalysisBlock

class KeyTerm(BaseModel):
    term: str                    # 용어 이름 (예: "연준", "기준 금리")
    definition: str              # 이게 뭔지 한국어로 설명
    analogy: Optional[str] = None  # 비유/직관적 설명 (없으면 None)

class EncyclopediaResponse(BaseModel):
    
    query_analysis: QueryAnalysisBlock   # 공통: 쿼리 유효성 분석 결과
    
    input_text: str                      # 원본 입력 문장
    key_terms: List[KeyTerm]             # 어려운 용어/개념 리스트
    simplified_explanation: str          # 전체 문장을 쉽게 풀어쓴 설명
    usage_context: Optional[str] = None  # 어떤 상황에서 쓰이는 표현인지
    extra_notes: Optional[str] = None    # 추가로 알면 좋은 배경지식
