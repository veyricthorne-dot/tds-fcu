from github import Github, Auth
from openai import OpenAI
from dotenv import load_dotenv
import os

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()

# -------------------------
# GitHub Test
# -------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")

if not GITHUB_TOKEN:
    raise ValueError("❌ Missing GITHUB_TOKEN in .env file")

auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)

# Get authenticated user
user = g.get_user()
print(f"👤 GitHub Authenticated as: {user.login}")

if USERNAME and user.login != USERNAME:
    print(f"⚠️ Warning: .env username ({USERNAME}) doesn't match actual login ({user.login})")

print("\n📂 Your first 5 GitHub repos:")
for repo in list(user.get_repos())[:5]:
    print("-", repo.name)

# -------------------------
# OpenAI Test
# -------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

# Create OpenAI client
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL or "https://api.openai.com/v1"
)

try:
    response = client.models.list()
    print("\n✅ OpenAI Authenticated. Available models:")
    for m in response.data[:5]:
        print("-", m.id)
except Exception as e:
    print("\n❌ OpenAI API failed:", e)
