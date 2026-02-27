import httpx
import logging

# 디버그 로그 활성화
logging.basicConfig(level=logging.DEBUG)

client = httpx.Client(timeout=30.0)

try:
    print("서버에 요청을 보냅니다. 최대 30초 대기합니다...")
    # 35초 동안 일부러 응답을 안 하는 테스트 서버 호출
    response = client.get("https://httpstat.us/200?sleep=35000") 
    print("응답 완료:", response.status_code)
except httpx.TimeoutException:
    print("서버 응답 시간이 30초를 초과하여 강제 종료되었습니다. (타임아웃 정상 작동)")