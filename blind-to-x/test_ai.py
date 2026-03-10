import asyncio
import sys
if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from config import ConfigManager, load_env, setup_logging
from pipeline.draft_generator import TweetDraftGenerator
from pipeline.image_generator import ImageGenerator
from pipeline.cost_tracker import CostTracker

async def test_draft():
    load_env()
    setup_logging()
    cfg = ConfigManager()
    
    cost_tracker = CostTracker(cfg)
    draft_gen = TweetDraftGenerator(cfg, cost_tracker=cost_tracker)
    img_gen = ImageGenerator(cfg, cost_tracker=cost_tracker)
    
    post_data = {
        "title": "이번 프로젝트 진짜 너무 힘들다",
        "content": "매일 야근에 주말출근에... 제대로 된 보상도 없이 갈려나가는 중입니다. 다른 동기들 보니까 이직할 타이밍인 것 같기도 하고... 진짜 퇴사 마렵네요. 이럴 땐 어떻게 멘탈 관리하시나요? 조언 부탁드립니다.",
        "url": "https://example.com/post",
        "category": "블라인드",
        "views": 1000,
        "likes": 50,
        "comments": 20
    }
    print("Generating drafts...")
    drafts, img_prompt = await draft_gen.generate_drafts(post_data)
    print("--- DRAFTS ---")
    print(drafts)
    print("--- IMG PROMPT ---")
    print(img_prompt)

    print("\nGenerating image...")
    # Mock image generation to avoid real DALL-E costs if needed, but since we are testing:
    # img_path = await img_gen.generate_image(img_prompt)
    # print(f"--- IMG PATH: {img_path} ---")
    
    print("\n--- COST TRACKER SUMMARY ---")
    print(cost_tracker.get_summary())

if __name__ == "__main__":
    asyncio.run(test_draft())
