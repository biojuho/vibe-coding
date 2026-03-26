from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
import pytest  # noqa: E402
from unittest.mock import MagicMock, mock_open, patch  # noqa: E402

# 우리가 만든 기능(모듈)들을 이곳으로 불러와서 테스트를 준비합니다.
from pipeline.utils import async_run_with_retry  # noqa: E402
from pipeline.image_upload import ImageUploader  # noqa: E402


class FakeConfig:
    """ImageUploader 초기화에 필요한 설정을 흉내 내는 가짜 설정 객체입니다."""

    _DEFAULTS: dict = {
        "image_hosting.provider": "imgur",
        "image_hosting.imgur.client_id": None,
        "image_hosting.cloudinary.cloud_name": None,
        "image_hosting.cloudinary.api_key": None,
        "image_hosting.cloudinary.api_secret": None,
        "request.retries": "3",
        "request.backoff_seconds": "1.5",
    }

    def get(self, key, default=None):
        return self._DEFAULTS.get(key, default)

# ==============================================================================
# ① 단위 테스트 (Unit Test) - 하나의 작은 부품(함수)이 튼튼한지 검사합니다.
# 프론트엔드의 Vitest 역할을 파이썬의 Pytest가 대신합니다!
# 대상: async_run_with_retry (실패 시 시간을 두고 여러 번 찔러보는 공통 기능)
# ==============================================================================
# @pytest.mark.asyncio는 "비동기(시간이 예측 안 되는) 테스트를 돌려달라"는 명령어입니다.
@pytest.mark.asyncio
class TestAsyncRunWithRetry:

    # [정상 케이스 1] 1번째 시도만에 바로 성공할 때
    async def test_success_on_first_try(self):
        # MagicMock은 진짜가 아닌 가짜(대역) 배우를 만들어 줍니다. "무조건 SUCCESS를 외쳐!"
        func = MagicMock(return_value="SUCCESS")
        result = await async_run_with_retry(func, max_retries=3, backoff_seconds=0.1)

        # 결과가 우리가 예상한 "SUCCESS"가 맞는지, 가짜 함수가 딱 1번만 불렸는지 확인(assert)합니다.
        assert result == "SUCCESS"
        assert func.call_count == 1

    # [정상 케이스 2] 1번 실패하고, 2번째 시도에서 겨우 성공할 때
    async def test_success_on_second_try(self):
        # side_effect: 차례대로 결과를 내놓는 가짜 배우 (첫 번째는 에러 연기, 두 번째는 성공 연기)
        func = MagicMock(side_effect=[Exception("일시적인 인터넷 끊김"), "SUCCESS_AFTER_RETRY"])
        result = await async_run_with_retry(func, max_retries=3, backoff_seconds=0.1)

        assert result == "SUCCESS_AFTER_RETRY"
        assert func.call_count == 2 # 2번째에 성공했으니 총 2번 불렸어야 정상입니다.

    # [정상 케이스 3] 아무것도 반환하지 않는(None) 함수도 에러 없이 끝나는지 확인
    async def test_success_returns_none(self):
        func = MagicMock(return_value=None)
        result = await async_run_with_retry(func, max_retries=2, backoff_seconds=0.1)
        assert result is None
        assert func.call_count == 1

    # [엣지/경계값 케이스] 빈 값, 0과 같은 아슬아슬한 경계값
    async def test_edge_zero_retries(self):
        # max_retries(최대 기회)가 0번일 경우, 아예 실행도 못하고 에러를 내야 정상입니다.
        func = MagicMock(return_value="WILL_NOT_REACH")
        with pytest.raises(Exception): # pytest.raises: "여기서 무조건 Exception 터져야 해!"라는 뜻
            await async_run_with_retry(func, max_retries=0, backoff_seconds=0.1)

    async def test_edge_negative_backoff(self):
        # 대기 시간이 마이너스(-1)일 경우, 시간 여행을 할 수 없으므로 파이썬 자체 내장 ValueError가 터질 겁니다.
        func = MagicMock(side_effect=[Exception("Fail1"), Exception("Fail2")])
        with pytest.raises(ValueError):
            await async_run_with_retry(func, max_retries=2, backoff_seconds=-1)

    # [에러 케이스] 3번(최대 기회)을 모두 연달아 실패했을 때
    async def test_error_all_retries_fail(self):
        # 계속 "Critical Error"만 뿜는 덜떨어진 배우 배정
        func = MagicMock(side_effect=Exception("Critical Error"))

        # 모두 실패하면 최종적으로 밖으로 에러를 던져야 맞음
        with pytest.raises(Exception) as excinfo:
            await async_run_with_retry(func, max_retries=3, backoff_seconds=0.01)

        # 던져진 에러 안에 우리가 지정한 문구 "Critical Error"가 들어있는지, 총 3번 끝까지 시도했는지 검사
        assert "Critical Error" in str(excinfo.value)
        assert func.call_count == 3


# ==============================================================================
# ② 컴포넌트 테스트 - 마치 레고 블록 한 뭉텅이(클래스)가 유기적으로 잘 조립됐는지 검사합니다.
# 프론트엔드의 React Testing Library 역할을 여기서 합니다!
# 대상: ImageUploader 클래스 (처음 생성 시 준비 완료인지, 눌렀을 때(메서드 호출) 내부 부품이 잘 도는지)
# ==============================================================================
@pytest.mark.asyncio
class TestImageUploaderComponent:

    # [1. 렌더링 확인] -> 클래스가 정상적으로 초기화(만들어지는지) 되는지 확인
    async def test_image_uploader_initialization(self):
        uploader = ImageUploader(FakeConfig())
        # 생성된 uploader 녀석 주머니에 'imgur_client_id' 같은 필수 설정표가 제대로 들어갔는지 검사합니다.
        assert hasattr(uploader, "imgur_client_id")
        assert hasattr(uploader, "_upload_to_imgur")

    # [2. 버튼 클릭 이벤트] -> upload_from_url을 호출하면 내부 requests.post가 실제 호출되는지 확인
    # upload_from_url은 imgur 경로에서 requests.post를 직접 사용하므로 이를 가짜로 교체합니다.
    @patch("requests.post")
    async def test_upload_button_click_event(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True, "data": {"link": "https://i.imgur.com/test.jpg"}}
        mock_post.return_value = mock_response

        uploader = ImageUploader(FakeConfig())
        uploader.imgur_client_id = "test_key"

        # 사용자가 "업로드 해!" 하고 버튼을 누르는 셈입니다.
        result = await uploader.upload_from_url("http://example.com/test.jpg")

        # 가짜로 지정한 결과("~test.jpg")가 정상 반환되었고,
        assert result == "https://i.imgur.com/test.jpg"
        # 외부 HTTP 요청이 딱 1번 호출되었음을 입증합니다.
        mock_post.assert_called_once()

    # [3. props(필수 재료)가 없을 때 Fallback 확인] -> 인증 정보 없이 호출하면 None을 반환하고 안전하게 종료하는지
    async def test_missing_props_fallback_behavior(self):
        uploader = ImageUploader(FakeConfig())
        # API 인증키(티켓)를 쥐어주지 않고 일부러 압수합니다.
        uploader.imgur_client_id = None
        uploader.cloudinary_ready = False

        # 티켓이 없는데 들어가려고 시도하면? 프로그램이 죽지 않고 None을 반환해야 합니다.
        result = await uploader._upload_to_imgur("fake_path")
        assert result is None

        result_cloudinary = await uploader._upload_to_cloudinary("fake_path")
        assert result_cloudinary is None


# ==============================================================================
# ③ API 통신 테스트 - 우리 코드와 바깥 세상(네이버, Imgur API 등)이 대화할 때를 가정합니다.
# 프론트엔드의 MSW(Mock Service Worker) 역할을 Python의 patch(가짜 응답기)가 수행합니다.
# ==============================================================================
@pytest.mark.asyncio
class TestImageUploadAPI:

    # [1. 200번 상태(성공) 응답] MSW 핸들러 대체
    # builtins.open을 mock_open으로 교체해 실제 파일 없이도 파일 읽기를 시뮬레이션합니다.
    @patch("requests.post")
    @patch("builtins.open", mock_open(read_data=b"fake_image_bytes"))
    async def test_api_200_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True, "data": {"link": "https://i.imgur.com/success.jpg"}}
        mock_post.return_value = mock_response

        uploader = ImageUploader(FakeConfig())
        uploader.imgur_client_id = "fake_id"

        # 우편을 보내면 가짜 우체통이 무조건 위에서 정해준 200번 성공 데이터를 줍니다.
        result = await uploader._upload_to_imgur("fake.jpg")
        assert result == "https://i.imgur.com/success.jpg"

    # [2. 400번 상태(유효성 짬짜미 실패) 응답]
    @patch("requests.post")
    @patch("builtins.open", mock_open(read_data=b"fake_image_bytes"))
    async def test_api_400_validation_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error")
        mock_post.return_value = mock_response

        uploader = ImageUploader(FakeConfig())
        uploader.imgur_client_id = "fake_id"

        # _upload_to_imgur는 내부에서 예외를 잡아 None을 반환합니다 (파이프라인 중단 방지).
        result = await uploader._upload_to_imgur("fake.jpg")
        assert result is None

    # [3. 500번 상태(저쪽 서버 불남) 파업 케이스]
    @patch("requests.post")
    @patch("builtins.open", mock_open(read_data=b"fake_image_bytes"))
    async def test_api_500_server_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        uploader = ImageUploader(FakeConfig())
        uploader.imgur_client_id = "fake_id"

        # 서버 에러도 내부 예외 처리로 None을 반환합니다.
        result = await uploader._upload_to_imgur("fake.jpg")
        assert result is None
