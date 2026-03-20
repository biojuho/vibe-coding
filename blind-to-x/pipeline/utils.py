import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

async def async_run_with_retry(
    func: Callable[[], Any],
    max_retries: int,
    backoff_seconds: float,
    action_name: str = "Operation"
) -> Any:
    """
    일반(동기) 함수를 멈춤 없이(비동기로) 실행하고, 실패할 경우 점차 시간을 늘려가며(지수 백오프) 재시도하는 공통 유틸리티 함수입니다.

    [용어 해설]
    - 비동기(Async) 실행: 어떤 작업을 하는 동안 프로그램이 멈춰서 기다리지 않고, 다른 일도 동시에 할 수 있게 해주는 방식입니다.
    - 지수 백오프(Exponential Backoff): 에러가 났을 때 바로 다시 시도하지 않고, 재시도 간격(대기 시간)을 점점 늘려가며(1초->2초->3초...) 접근하는 기법입니다. 서버에 무리를 주지 않기 위해 사용합니다.
    - 실행기(Executor): 일반적인 동기 함수를 비동기처럼 백그라운드에서 안전하게 돌려주는 도구입니다.

    Args:
        func: 실행할 일반(동기) 함수 (예: requests.post 처럼 시간이 걸리는 통신 함수)
        max_retries: 최대 재시도 횟수
        backoff_seconds: 재시도 전 기본 대기 시간 (초 단위)
        action_name: 로그에 남길 작업의 이름 (무엇을 하다 실패했는지 알기 위해)

    Raises:
        Exception: 정해진 재시도 횟수를 모두 채워도 실패하면, 가장 마지막에 발생한 에러를 뿜어냅니다(raise).
    """
    if backoff_seconds < 0:
        raise ValueError(f"backoff_seconds must be non-negative, got {backoff_seconds}")

    last_err = None  # 가장 마지막에 발생한 에러를 보관할 변수 공간

    # 1번째 시도부터 max_retries(최대 재시도 횟수)까지 반복합니다.
    for attempt in range(1, max_retries + 1):
        try:
            # 현재 작동 중인 비동기 루프(구동 환경)를 가져옵니다.
            loop = asyncio.get_running_loop()

            # 들어온 함수(func)를 백그라운드 실행기(executor)에서 안전하게 돌리고, 끝날 때까지 기다립니다(await).
            return await loop.run_in_executor(None, func)

        except Exception as e:
            last_err = e  # 에러가 나면 일단 변수에 저장합니다.

            # 아직 최대 재시도 횟수에 도달하지 않았다면, 조금 쉬었다가 다시 시도합니다.
            if attempt < max_retries:
                # 쉬는 시간 = 기본 대기 시간 * 현재 시도 횟수 (즉, 갈수록 대기 시간이 늘어남)
                wait = backoff_seconds * attempt
                logger.warning(
                    f"[{action_name}] {attempt}/{max_retries}번째 시도 실패: {e}. {wait:.1f}초 뒤에 다시 시도합니다."
                )
                await asyncio.sleep(wait)  # 계산된 시간만큼 프로그램을 멈추지 않고(비동기) 부드럽게 대기합니다.

    # 모든 재시도가 실패하면 최종 에러 로그를 남기고 프로그램을 중단시킵니다.
    logger.error(f"[{action_name}] {max_retries}번의 시도가 모두 실패했습니다: {last_err}")
    raise last_err
