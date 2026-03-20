"""
이미지를 Imgur 또는 Cloudinary 서비스에 업로드하는 모듈입니다.

[어려운 용어 해설]
- Imgur / Cloudinary: 이미지를 인터넷 상에 저장하고 누구나 볼 수 있는 고유한 무료 주소(URL)를 발급해주는 외부 호스팅 서비스입니다.
- base64: 이미지 파일 같은 바이너리(컴퓨터가 읽는 원본) 데이터를, 일반적인 영어 알파벳과 숫자 조합으로 된 긴 텍스트 문자로 변환하는 공식입니다. 파일을 안전하게 전송할 때 활용합니다.
- 페이로드(Payload): 전송하는 요청(택배 상자) 안에 실제로 담겨 있는 핵심 내용물(데이터)을 말합니다.
- 예외 처리(Exception Handling): 프로그램이 중간에 에러(장애물)를 만나도 멈추지 않고, 정해진 다른 길(우회로)로 가도록 안전장치를 마련하는 것입니다.
"""

import asyncio
import base64
import logging
import os
import tempfile

import requests
import cloudinary
import cloudinary.uploader

from .utils import async_run_with_retry

logger = logging.getLogger(__name__)

# Cloudinary 무료 플랜 업로드 한도 대비 안전 마진 (9MB < 10MB 한도)
_MAX_UPLOAD_BYTES = 9 * 1024 * 1024  # 9 MB


def _optimize_image_for_upload(filepath: str, max_bytes: int = _MAX_UPLOAD_BYTES) -> str:
    """이미지 파일이 max_bytes를 초과하면 자동으로 압축/리사이즈하여 임시 파일로 반환합니다.

    1단계: PNG → JPEG 변환 (투명 배경은 흰색으로 채움)
    2단계: JPEG quality를 점진적으로 낮춤 (85 → 70 → 55 → 40)
    3단계: quality로 부족하면 해상도를 80%씩 축소

    원본 파일이 이미 한도 이내이면 원본 경로를 그대로 반환합니다.
    """
    file_size = os.path.getsize(filepath)
    if file_size <= max_bytes:
        return filepath

    logger.info(
        "이미지 최적화 시작: %.1fMB → 목표 %.1fMB 이하 (%s)",
        file_size / 1024 / 1024,
        max_bytes / 1024 / 1024,
        os.path.basename(filepath),
    )

    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow가 설치되지 않아 이미지 최적화를 건너뜁니다. pip install Pillow")
        return filepath

    try:
        img = Image.open(filepath)

        # RGBA/P → RGB (투명 배경을 흰색으로 채움)
        if img.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # 점진적 품질 감소 시도
        quality_steps = [85, 70, 55, 40]
        for quality in quality_steps:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()
            img.save(tmp.name, format="JPEG", quality=quality, optimize=True)
            new_size = os.path.getsize(tmp.name)

            if new_size <= max_bytes:
                logger.info(
                    "이미지 최적화 완료: %.1fMB → %.1fMB (quality=%d)",
                    file_size / 1024 / 1024,
                    new_size / 1024 / 1024,
                    quality,
                )
                return tmp.name
            os.unlink(tmp.name)

        # 품질 감소만으로 부족 → 해상도 축소
        scale = 0.8
        for _ in range(5):
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            if new_w < 400 or new_h < 400:
                break
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()
            resized.save(tmp.name, format="JPEG", quality=55, optimize=True)
            new_size = os.path.getsize(tmp.name)

            if new_size <= max_bytes:
                logger.info(
                    "이미지 최적화 완료: %.1fMB → %.1fMB (resize=%dx%d, quality=55)",
                    file_size / 1024 / 1024,
                    new_size / 1024 / 1024,
                    new_w,
                    new_h,
                )
                return tmp.name
            os.unlink(tmp.name)
            scale *= 0.8

        logger.warning("이미지 최적화 실패: 모든 시도 후에도 %.1fMB. 원본으로 업로드 시도.", file_size / 1024 / 1024)
        return filepath

    except Exception as exc:
        logger.warning("이미지 최적화 중 오류 발생 (원본으로 진행): %s", exc)
        return filepath


class ImageUploader:
    """이미지 업로드를 전담하는 메인 도우미(클래스)입니다."""

    def __init__(self, config):
        self.config = config
        # 설정 파일에서 기본 업로드 서비스(provider)를 가져옵니다. 별도 지정이 없으면 기본값 'imgur'를 사용합니다.
        self.provider = config.get("image_hosting.provider", "imgur")
        self.imgur_client_id = config.get("image_hosting.imgur.client_id")

        # 외부 통신 실패 시 최대 몇 번을 재시도할지, 대기 시간은 몇 초로 할지 설정합니다.
        self.max_retries = int(config.get("request.retries", 3))
        self.backoff = float(config.get("request.backoff_seconds", 1.5))

        # 만약 시스템 환경 변수(env vars)에 보안이 중요한 IMGUR 키가 숨겨져 있다면 그걸 우선적으로 덮어씌워 씁니다.
        env_client_id = os.environ.get("IMGUR_CLIENT_ID")
        if env_client_id:
            self.imgur_client_id = env_client_id

        # Cloudinary(클라우디너리) 접속 설정 초기화
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME") or config.get("image_hosting.cloudinary.cloud_name")
        api_key = os.environ.get("CLOUDINARY_API_KEY") or config.get("image_hosting.cloudinary.api_key")
        api_secret = os.environ.get("CLOUDINARY_API_SECRET") or config.get("image_hosting.cloudinary.api_secret")

        # Cloudinary 인증 정보가 모두 채워져 있으면 공식 연결을 수립(설정)합니다.
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True, # 안전한 HTTPS 통신을 강제합니다.
            )
            self.cloudinary_ready = True
        else:
            self.cloudinary_ready = False

    async def upload(self, filepath):
        """내 컴퓨터(로컬)에 있는 이미지 파일을 지정된 인터넷 서비스(Imgur/Cloudinary)로 업로드합니다."""
        # 1. 파일이 실제로 우리 컴퓨터에 존재하는지 확인합니다.
        if not os.path.exists(filepath):
            logger.error(f"지정된 파일을 찾을 수 없습니다: {filepath}")
            return None

        # 2. 파일 용량이 너무 작은지도 검사합니다 (1000 바이트 미만이면 속이 빈 껍데기 파일일 확률이 높음).
        if os.path.getsize(filepath) < 1000:
            logger.error(f"스크린샷 파일 용량이 너무 작아 손상된 것으로 보입니다 ({os.path.getsize(filepath)} bytes): {filepath}")
            return None

        # 3. 설정된 제공자(provider) 이름표에 따라 알맞은 업로드 함수를 골라서 호출합니다.
        #    Cloudinary는 10MB 제한이 있으므로 업로드 전 자동 최적화를 적용합니다.
        if self.provider == "cloudinary":
            filepath = _optimize_image_for_upload(filepath)

        if self.provider == "imgur":
            return await self._upload_to_imgur(filepath)
        elif self.provider == "cloudinary":
            return await self._upload_to_cloudinary(filepath)
        else:
            # 설정 메뉴에 오타가 있거나 지원하지 않는 제공자면 경고를 띄우고 가장 기본적인 Imgur로 업로드를 대체 시도(Fallback)합니다.
            logger.warning(f"지원하지 않는 업로드 제공자입니다: {self.provider}. 자동으로 Imgur 업로드를 시도합니다.")
            if self.imgur_client_id:
                return await self._upload_to_imgur(filepath)
            return None

    async def upload_from_url(self, url):
        """내 컴퓨터에 파일이 없어도, 이미 인터넷 언딘가(URL)에 있는 이미지를 그대로 가져와서 우리 서비스로 재업로드합니다 (예: AI가 방금 그려낸 이미지)."""
        logger.info(f"URL로부터 이미지를 직접 업로드합니다: {url[:50]}...")

        if self.provider == "cloudinary":
            # Cloudinary는 URL을 그대로 주어도 알아서 서버가 직접 긁어와 업로드해 줍니다.
            return await self._upload_to_cloudinary(url)

        elif self.provider == "imgur":
            # Imgur 역시 URL 다이렉트 업로드를 지원합니다.
            if not self.imgur_client_id:
                return None

            headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
            payload = {"image": url, "type": "url"} # base64 방식 대신 URL 문자열이라고 명시해서 전송합니다.

            # 실제 Imgur 서버와 우체부 역할을 하며 통신을 맺는 내부 함수입니다 (비동기가 아님).
            def do_request():
                response = requests.post("https://api.imgur.com/3/image", headers=headers, data=payload, timeout=30)
                response.raise_for_status() # 성공(200번대 응답)이 아니면 그 즉시 에러 불꽃(Exception)을 일으킵니다.
                return response.json()

            try:
                # 위에서 만든 'utils.py'의 공통 유틸리티를 사용해, 실패 시 시간 텀을 두고 부드럽게 재시도(지수 백오프)를 맡깁니다.
                data = await async_run_with_retry(
                    func=do_request,
                    max_retries=self.max_retries,
                    backoff_seconds=self.backoff,
                    action_name="Imgur URL 다이렉트 업로드"
                )

                # 통신이 최종 성공했고 돌려받은 상자(딕셔너리) 안에 이미지 주소(link)가 들어 있다면 무사히 반환합니다!
                if data.get("success") and data.get("data", {}).get("link"):
                    return data["data"]["link"]
            except Exception as e:
                logger.error(f"Imgur에 URL 기반 이미지를 업로드하는 데 실패했습니다: {e}")
                return None
        return None


    async def _upload_to_imgur(self, filepath):
        """Imgur 서비스에 로컬 컴퓨터의 파일을 올려주는 숨겨진 내부 조수 함수(메서드)입니다."""
        if not self.imgur_client_id:
            logger.error("Imgur Client-ID (필수 인증 열쇠)가 없습니다.")
            return None

        logger.info(f"Imgur에 파일 업로드 진행 중... 대상 파일: {filepath}")

        # 사진 파일을 컴퓨터가 편하게 읽을 수 있는 base64 문자열 형태로 잘게 쪼개어 번역(인코딩)합니다.
        with open(filepath, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode("utf-8")

        headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        payload = {"image": encoded_string, "type": "base64"}

        # Imgur 서버 대문으로 택배를 보내는 통신 로직입니다.
        def do_request():
            response = requests.post(
                "https://api.imgur.com/3/image",
                headers=headers,
                data=payload,
                timeout=30, # 30초 동안 응답이 없으면 포기(타임아웃)합니다.
            )
            response.raise_for_status() # 비정상 응답이면 예외 발생

            try:
                return response.json() # 결과물을 다루기 편한 Python 사전(딕셔너리)으로 해석합니다.
            except ValueError as json_err:
                # JSON 해석에 실패하면(서버가 이상한 글자를 줬다면) 에러의 단서를 수집해 다시 에러를 던집니다.
                preview = response.text[:200] if hasattr(response, "text") else "(응답 내용-몸통 없음)"
                raise RuntimeError(
                    f"Imgur API가 약속된 형태(JSON)로 대답하지 않았습니다. "
                    f"(상태코드={response.status_code}): {preview}"
                ) from json_err

        try:
            # 실패 시 알아서 여유를 두고 재차 시도하는 믿음직한 공통 요원(utils)에게 맡깁니다.
            data = await async_run_with_retry(
                func=do_request,
                max_retries=self.max_retries,
                backoff_seconds=self.backoff,
                action_name="Imgur 로컬 파일 업로드"
            )

            if data.get("success") and data.get("data", {}).get("link"):
                link = data["data"]["link"]
                logger.info(f"✨ 업로드 대성공! 발급된 링크: {link}")
                return link
            else:
                logger.error(f"Imgur API가 정상적으로 처리를 끝마치지 못했습니다: {data}")
                return None
        except Exception:
            # 최종 실패 시 아무 것도 반환하지 않습니다(None)
            return None

    async def _upload_to_cloudinary(self, filepath):
        """Cloudinary 서비스에 로컬 파일 또는 이미 존재하는 다른 URL을 업로드하는 내부 조수 함수입니다."""
        if not self.cloudinary_ready:
            logger.error("Cloudinary 인증 계정 정보가 누락되었거나 한 개 이상 비어있어, 서버 창구를 열지 못했습니다.")
            return None

        logger.info(f"Cloudinary에 업로드 진행 중... 대상: {filepath}")

        # Cloudinary 전용 택배원(라이브러리 uploader)에게 일을 넘깁니다. 
        # (주의: 이 친구는 아주 간단해 보이지만 내부적으로 무수히 많은 통신 규칙을 혼자 처리하고 있습니다)
        def do_request():
            response = cloudinary.uploader.upload(filepath)
            link = response.get("secure_url") # 'https(보안)'가 적용된 안전한 이미지 주소를 확보합니다.
            if link:
                return link

            # 예상치 못한 엉뚱한 응답 포맷일 경우
            raise RuntimeError(f"Cloudinary로부터 예상치 못한 형태의 응답을 받았습니다: {response}")

        try:
            # 네트워크 불안정, 순간 끊김 현상을 대비하여 지수 백오프 기반 재시도를 적용합니다.
            link = await async_run_with_retry(
                func=do_request,
                max_retries=self.max_retries,
                backoff_seconds=self.backoff,
                action_name="Cloudinary 공식 라이브러리 업로드"
            )
            logger.info(f"✨ 업로드 완료 (보안 링크 획득): {link}")
            return link
        except Exception:
            return None
