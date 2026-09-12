from app.core.post_processor import PostProcessor

processor = PostProcessor()

code = """
@app.get("/.env")
def get_env():
    return "secret"
"""

fixed, warnings = processor.process(code)
print("=" * 50)
print("WARNINGS:", warnings)
print("=" * 50)
print("FIXED CODE:")
print(fixed)
print("=" * 50)
