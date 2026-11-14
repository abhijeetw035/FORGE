import os

# The API refuses to start without a strong key. Tests get a throwaway one
# unless the environment already provides a real one.
os.environ.setdefault("SECRET_KEY", "test-only-" + "x" * 48)
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
