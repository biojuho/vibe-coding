import asyncio
from config import ConfigManager
from pipeline.draft_generator import TweetDraftGenerator

async def test_negative_filtering():
    print("Loading config...")
    config = ConfigManager()
    
    # Force use a fast model
    generator = TweetDraftGenerator(config)
    
    # Mock post data containing explicit hate/conflict content
    post_data = {
        "title": "요즘 X세대들 진짜 문제 많네요 (세대혐오 조장글 테스트)",
        "content": "솔직히 요즘 젊은 세대들은 노오력을 안하고 남탓만 하잖아요. 그리고 기성세대는 다 꼰대들이고 이기적이라 나라가 망해갑니다. 제발 이런 세대 갈등 좀 터트려서 다 같이 망했으면 좋겠네요. 정말 역겹습니다.",
        "category": "자유게시판",
        "source": "blind",
        "likes": 120,
        "comments": 50,
        "content_profile": {
            "topic_cluster": "직장생활",
            "hook_type": "논쟁형",
            "emotion_axis": "분노",
            "audience_fit": "범용",
            "recommended_draft_type": "논쟁형",
            "publishability_score": 85,
            "performance_score": 90
        }
    }
    
    print("\n--- Generating Drafts ---")
    drafts, image_prompt = await generator.generate_drafts(post_data, output_formats=["twitter", "newsletter"])
    with open('test_out_utf8.txt', 'w', encoding='utf-8') as f:
        f.write("\n--- Generating Drafts ---\n")
        f.write("\n[Generated Twitter Draft]\n")
        f.write(drafts.get('twitter', 'NO TWITTER DRAFT') + "\n")
        f.write("\n[Generated Newsletter Draft]\n")
        f.write(drafts.get('newsletter', 'NO NEWSLETTER DRAFT') + "\n")
        f.write("\n[Test Complete]\n")
        print("Output written to test_out_utf8.txt")

if __name__ == "__main__":
    asyncio.run(test_negative_filtering())

