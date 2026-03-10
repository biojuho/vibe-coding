import os
import sys
import time
from dotenv import load_dotenv

# ?덈룄???몄퐫???ㅼ젙
def _configure_utf8_stdio():
    # Running this unconditionally during test import breaks pytest capturing.
    import io
    if hasattr(sys.stdout, "detach"):
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8")
    if hasattr(sys.stderr, "detach"):
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding="utf-8")

if __name__ == "__main__":
    _configure_utf8_stdio()
# Google Credentials ?섍꼍蹂???ㅼ젙 (?꾩옱 ?붾젆?좊━ 湲곗?)
current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(current_dir, "credentials.json")

print(f"[INFO] Credentials Path: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")

try:
    from notebooklm_mcp.server import get_client
except ImportError:
    get_client = None
    if __name__ == "__main__":
        print("[FAIL] notebooklm_mcp package is not available. Run this in the notebooklm-mcp venv.")
        sys.exit(1)

def test_performance():
    if get_client is None:
        import pytest
        pytest.skip("notebooklm_mcp package is not installed in this environment.")
    print("\n?? [Step 1] NotebookLM ?대씪?댁뼵???곌껐 以?..")
    try:
        client = get_client()
        user_info = client.get_user_info() if hasattr(client, 'get_user_info') else "User info not available"
        print(f"??[?깃났] ?몄쬆 ?꾨즺! (User: {user_info})")
    except Exception as e:
        print(f"??[?ㅽ뙣] ?몄쬆 ?ㅻ쪟 諛쒖깮: {e}")
        print("  -> 'authenticate_notebooklm.bat'瑜??ㅽ뻾?섏뿬 ?ㅼ떆 濡쒓렇?명빐二쇱꽭??")
        return

    print("\n?뱮 [Step 2] ?뚯뒪?몄슜 ?명듃遺??앹꽦 以?..")
    try:
        title = "[Antigravity] Performance Test ?㎦"
        notebook = client.create_notebook(title=title)
        print(f"??[?깃났] ?명듃遺??앹꽦?? {notebook.title}")
        print(f"   -> ID: {notebook.id}")
        print(f"   -> URL: https://notebooklm.google.com/notebook/{notebook.id}")
    except Exception as e:
        print(f"??[?ㅽ뙣] ?명듃遺??앹꽦 ?ㅻ쪟: {e}")
        return

    print("\n?뱞 [Step 3] ?뚯뒪 ?곗씠??異붽? (Antigravity ?꾨줈?앺듃 ?뺣낫)...")
    try:
        # ?뚯뒪?몄슜 臾몄꽌 ?곗씠??
        project_overview = """
        ?꾨줈?앺듃紐? Antigravity (諛섏쨷??
        
        [媛쒖슂]
        Antigravity ?꾨줈?앺듃??AI ?먯씠?꾪듃 '?쇳봽(Raf)'? ?④퍡 媛쒖씤???앹궛?깆쓣 洹밸??뷀븯怨? 
        ?몄긽???몃젋?쒕? 鍮좊Ⅴ寃??ъ갑?섏뿬 ?몄궗?댄듃瑜??쒓났?섎뒗 ?쒖뒪?쒖엯?덈떎.
        
        [?듭떖 紐⑤뱢]
        1. Notion MCP: 
           - 媛쒖씤??????Task), ?꾩씠?붿뼱, 踰꾧렇 由ы룷???깆쓣 Notion ?곗씠?곕쿋?댁뒪???먮룞?쇰줈 湲곕줉?⑸땲??
           - V2 ?낅뜲?댄듃瑜??듯빐 ?좎쭨, 紐⑺몴, ?ъ꽦 ?댁슜 ?깆쓽 ?곸꽭 ?띿꽦??吏?먰빀?덈떎.
           
        2. NotebookLM MCP:
           - 援ш???NotebookLM怨??곕룞?섏뿬 諛⑸???臾몄꽌瑜??댄빐?섍퀬 吏덉쓽?묐떟?????덉뒿?덈떎.
           - ?ъ슜?먭? 吏곸젒 臾몄꽌瑜??쎌? ?딆븘???듭떖 ?댁슜???붿빟?댁＜怨? 蹂듭옟??吏덈Ц???듯빐以띾땲??
           
        3. X(Twitter) Trend Analysis (?덉젙):
           - Brave Search瑜??듯빐 ?ㅼ떆媛??몃젋?쒕? ?뚯븙?섍퀬, ?몄궗?댄듃 由ы룷?몃? ?묒꽦?⑸땲??
        
        [???
        - User: ?꾨줈?앺듃 珥앷큵 諛??섏궗寃곗젙
        - Raf (AI): 媛쒕컻, 湲고쉷, ?ㅽ뻾???대떦?섎뒗 理쒓퀬???뚰듃??
        """
        
        source = client.add_text_source(notebook.id, project_overview, title="Antigravity Project Overview")
        # 諛섑솚媛믪씠 dict??寃쎌슦 泥섎━
        if isinstance(source, dict):
             source_title = source.get('title', 'Unknown Title')
        else:
             source_title = source.title
             
        print(f"??[?깃났] ?뚯뒪 異붽??? {source_title}")
        print("   -> ?댁슜 泥섎━瑜??꾪빐 ?좎떆 ?湲고빀?덈떎 (5珥?...")
        time.sleep(5) 
    except Exception as e:
        print(f"??[?ㅽ뙣] ?뚯뒪 異붽? ?ㅻ쪟: {e}")
        return

    print("\n?뮠 [Step 4] AI 吏덉쓽?묐떟 ?뚯뒪??..")
    questions = [
        "???꾨줈?앺듃???듭떖 紐⑤뱢 3媛吏??臾댁뾿?멸???",
        "?쇳봽(Raf)????븷? 萸먯빞?"
    ]
    
    for q in questions:
        print(f"\nQ: {q}")
        try:
            # query 硫붿꽌?쒕뒗 dict媛 ?꾨땲??媛앹껜瑜?諛섑솚???섎룄 ?덇퀬 dict瑜?諛섑솚???섎룄 ?덉쓬.
            # server.py 濡쒖쭅??client.query() ?몄텧 寃곌낵瑜?洹몃?濡??.
            # NotebookLMClient.query??諛섑솚媛믪쓣 ?뺤씤?댁빞 ?? 蹂댄넻 dict??
            answer_obj = client.query(notebook.id, q)
            
            # answer_obj媛 dict?몄? 媛앹껜?몄? ?뺤씤?섏뿬 泥섎━
            answer_text = ""
            if isinstance(answer_obj, dict):
                answer_text = answer_obj.get("answer", "No answer found")
            else:
                answer_text = getattr(answer_obj, "answer", str(answer_obj))
                
            print(f"A: {answer_text}")
            print("-" * 50)
        except Exception as e:
            print(f"??[?ㅽ뙣] 吏덉쓽 ?ㅻ쪟: {e}")

    print("\n??[?꾨즺] 紐⑤뱺 ?뚯뒪?멸? 醫낅즺?섏뿀?듬땲??")

if __name__ == "__main__":
    test_performance()

