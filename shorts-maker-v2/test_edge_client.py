import asyncio
from pathlib import Path
from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient

def main():
    client = EdgeTTSClient()
    out = Path("test_audio.mp3")
    words = Path("test_words.json")
    if out.exists(): out.unlink()
    if words.exists(): words.unlink()

    client.generate_tts(
        model="",
        voice="ko-KR-SunHiNeural",
        speed=1.0,
        text="이것은 후크 <테스트>입니다! 시선을 집중시키세요!",
        output_path=out,
        words_json_path=words,
        role="hook"
    )
    print("Done generating hook.")

if __name__ == "__main__":
    main()
