# schemas/common.py
"""
AdapDict 공통 스키마 정의

여기에는 여러 generator 스키마(word, sentence, paragraph, encyclopedia 등)에서
공유해서 사용할 공통 Pydantic 모델들을 정의한다.

현재 포함된 것:
- QueryAnalysisStatus: Query 유효성 상태를 나타내는 Literal 타입
- QueryAnalysisBlock: Query 유효성 분석 결과 블록
"""

from typing import List, Literal, Optional
from pydantic import BaseModel


# Query가 어떤 상태인지 표현하는 타입
QueryAnalysisStatus = Literal[
    "VALID",          # 정상적인 Query
    "TYPO",           # 오타/철자 오류가 있는 경우
    "FACTUAL_ERROR",  # 내용이 사실과 다른 경우
    "AMBIGUOUS",      # 정보가 부족하거나 의도가 모호한 경우
    "NONSENSE",       # 문장이 논리적으로 성립하지 않는 경우
]


class QueryAnalysisBlock(BaseModel):
    """
    메인 LLM이 'Query 자체'를 먼저 평가한 결과를 담는 블록.

    모든 응답 스키마(단어/문장/문단/백과)에 공통으로 포함된다.
    """

    # 위에서 정의한 5가지 상태 중 하나
    status: QueryAnalysisStatus

    # 왜 그렇게 판단했는지 한국어로 설명
    #   예) "입력하신 'applr'는 알려진 영어 단어가 아니며, 'apple'의 오타일 가능성이 높습니다."
    reason_l1: str # 모국어로 출력

    # 오타인 경우, 사용자가 다시 검색해 볼 것을 제안할 후보 Query 목록
    #   예) ["apple", "apply"]
    # FACTUAL_ERROR / AMBIGUOUS / NONSENSE 인 경우에는 보통 None 또는 빈 리스트
    suggestion_queries: Optional[List[str]] = None

    @property
    def is_valid(self) -> bool:
        """
        헬퍼 프로퍼티: status가 VALID인지 여부를 간단히 확인할 때 사용.
        main.py나 다른 곳에서 `entry.query_analysis.is_valid`로 사용할 수 있다.
        """
        return self.status == "VALID"
