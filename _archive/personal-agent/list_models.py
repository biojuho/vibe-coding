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

if not GOOGLE_API_KEY:
    print("GOOGLE_API_KEY not found in config/env")
    exit()

print(f"Using API Key: {GOOGLE_API_KEY[:5]}...")

print("Listing models...")
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
                print(f"Model: {model.name}")
                print(f"Supported methods: {supported}")
                print("-" * 20)
        finally:
            client.close()
    elif legacy_genai is not None:
        legacy_genai.configure(api_key=GOOGLE_API_KEY)
        for model in legacy_genai.list_models():
            print(f"Model: {model.name}")
            print(f"Supported methods: {model.supported_generation_methods}")
            print("-" * 20)
    else:
        print("Google GenAI SDK not installed.")
except Exception as e:
    print(f"Error listing models: {e}")
