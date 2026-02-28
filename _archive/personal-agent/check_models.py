import warnings

from config import GOOGLE_API_KEY

google_genai = None
legacy_genai = None

try:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*_UnionGenericAlias.*deprecated.*",
            category=DeprecationWarning,
            module=r"google\.genai\.types",
        )
        from google import genai as google_genai
except ImportError:
    google_genai = None

if google_genai is None:
    try:
        import google.generativeai as legacy_genai
    except ImportError:
        legacy_genai = None

print("Listing available models...")
try:
    if google_genai is not None:
        client = google_genai.Client(api_key=GOOGLE_API_KEY)
        try:
            for model in client.models.list():
                supported = getattr(model, "supported_actions", None) or getattr(
                    model,
                    "supported_generation_methods",
                    [],
                )
                normalized = {str(item).lower() for item in supported}
                if not normalized or any(
                    token in normalized
                    for token in ("generatecontent", "generate_content")
                ):
                    print(model.name)
        finally:
            client.close()
    elif legacy_genai is not None:
        legacy_genai.configure(api_key=GOOGLE_API_KEY)
        for model in legacy_genai.list_models():
            if "generateContent" in model.supported_generation_methods:
                print(model.name)
    else:
        print("Google GenAI SDK not installed.")
except Exception as e:
    print(f"Error listing models: {e}")
