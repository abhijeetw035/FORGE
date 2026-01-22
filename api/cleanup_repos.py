import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Connect to DB
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/forge")
engine = create_engine(DATABASE_URL)

def cleanup():
    print("🔍 Scanning repositories...")
    
    with engine.connect() as conn:
        # Check how many repos exist
        result = conn.execute(text("SELECT COUNT(*) FROM repositories WHERE name != 'Java-testgen-suite'"))
        count = result.scalar()
        
        if count == 0:
            print("✅ No repositories to delete!")
            return
        
        print(f"⚠️  Found {count} repositories to delete.")
        
        # Get repository IDs to delete
        result = conn.execute(text("SELECT id, name FROM repositories WHERE name != 'Java-testgen-suite'"))
        repos = [(row[0], row[1]) for row in result]
        
        if not repos:
            print("✅ No repositories to delete!")
            return
        
        print("💥 Deleting repositories one by one...")
        
        for repo_id, repo_name in repos:
            print(f"\n   📦 Processing: {repo_name} (ID: {repo_id})")
            
            # Count data
            result = conn.execute(text(f"SELECT COUNT(*) FROM commits WHERE repository_id = {repo_id}"))
            commit_count = result.scalar()
            print(f"      Found {commit_count} commits")
            
            # Delete functions for this repo's commits
            print(f"      🗑️  Deleting functions...")
            conn.execute(text(f"DELETE FROM functions WHERE commit_id IN (SELECT id FROM commits WHERE repository_id = {repo_id})"))
            conn.commit()
            
            # Delete commits
            print(f"      🗑️  Deleting commits...")
            conn.execute(text(f"DELETE FROM commits WHERE repository_id = {repo_id}"))
            conn.commit()
            
            # Delete repository
            print(f"      🗑️  Deleting repository...")
            conn.execute(text(f"DELETE FROM repositories WHERE id = {repo_id}"))
            conn.commit()
            
            print(f"      ✅ {repo_name} deleted successfully!")
        
        print("\n✅ All deletions complete!")
        
        # Verify
        result = conn.execute(text("SELECT name FROM repositories"))
        remaining = [row[0] for row in result]
        print(f"📋 Remaining repositories: {remaining}")

if __name__ == "__main__":
    cleanup()
