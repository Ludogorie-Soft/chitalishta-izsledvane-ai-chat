import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from langsmith import Client
from app.core.config import settings

def test_connection():
    print(f"Testing LangSmith connection...")
    print(f"Endpoint: {settings.langchain_endpoint}")
    print(f"Project: {settings.langchain_project}")
    print(f"API Key: {settings.langchain_api_key[:10]}...")
    
    try:
        client = Client(
            api_url=settings.langchain_endpoint,
            api_key=settings.langchain_api_key,
        )
        
        # Try to read the project
        print("\nAttempting to read project...")
        if client.has_project(settings.langchain_project):
            print(f"✅ Project '{settings.langchain_project}' exists!")
        else:
            print(f"⚠️ Project '{settings.langchain_project}' not found. It will be created on first trace.")
            
        # Try to list projects to verify auth
        print("\nListing projects to verify auth...")
        projects = list(client.list_projects(limit=5))
        print(f"✅ Auth successful! Found {len(projects)} projects.")
        for p in projects:
            print(f"  - {p.name}")
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
