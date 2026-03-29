from execution.code_evaluator import CodeEvaluator


class MockLLMClient:
    def __init__(self, mock_response: dict):
        self.mock_response = mock_response

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3):
        if Exception in self.mock_response.values():
            raise ValueError("Mock LLM Exception")
        return self.mock_response


def test_code_evaluator_success():
    """정상적인 JSON 응답이 왔을 때 Pydantic 파싱 성공 여부 확인"""
    mock_llm = MockLLMClient(
        {
            "self_reflection": "코드가 완벽하게 요구사항을 충족하며 취약점이 없습니다.",
            "score": 0.95,
            "security_score": 1.0,
            "performance_score": 0.9,
            "readability_score": 0.9,
            "is_approved": True,
            "feedback": "",
        }
    )

    evaluator = CodeEvaluator(llm_client=mock_llm)
    res = evaluator.evaluate("req", "print('hello')")

    assert res.is_approved is True
    assert res.score == 0.95
    assert res.security_score == 1.0


def test_code_evaluator_llm_failure():
    """LLM이 예외를 발생시켰을 때 기본 EvaluationResult 반환(예외처리) 확인"""

    class FailingLLM:
        def generate_json(self, *args, **kwargs):
            raise ConnectionError("Network error")

    evaluator = CodeEvaluator(llm_client=FailingLLM())
    res = evaluator.evaluate("req", "code")

    assert res.is_approved is False
    assert res.score == 0.0
    assert "Network error" in res.self_reflection


# [QA 수정] 회귀 테스트 의무화 적용
def test_regression_evaluator_missing_fields():
    """
    [회귀 테스트] LLM이 실수로 필수 필드를 누락한 JSON을 반환할 때,
    Pydantic ValidationError가 발생하여 예외 처리 분기로 정상 폴백되는지 확인
    """
    mock_llm = MockLLMClient(
        {
            # "score", "is_approved" 등이 누락된 불완전한 JSON 응답
            "self_reflection": "불완전한 응답",
            "security_score": 0.5,
        }
    )

    evaluator = CodeEvaluator(llm_client=mock_llm)
    res = evaluator.evaluate("req", "code")

    # 파싱에 실패하면 Exception 분기를 타서 안전하게 is_approved=False 반환해야 함
    assert res.is_approved is False
    assert res.score == 0.0
    assert "validation error" in res.self_reflection.lower() or "파싱 중 오류 발생" in res.self_reflection
