#!/usr/bin/env python3
"""
Quick test script to verify The Oracle AI predictions
"""
import requests
import json

API_URL = "http://localhost:8000"

# Test credentials (use your actual login)
email = "test@example.com"
password = "testpass123"

def test_oracle():
    print("🔮 Testing The Oracle AI Risk Prediction Engine\n")
    
    # Step 1: Login
    print("1️⃣ Logging in...")
    login_response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": email, "password": password}
    )
    
    if login_response.status_code != 200:
        print(f" Login failed: {login_response.text}")
        print("\n💡 Update the email/password in test_oracle.py with your actual credentials")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful!\n")
    
    # Step 2: Get repositories
    print("2️⃣ Fetching repositories...")
    repos_response = requests.get(f"{API_URL}/repositories/", headers=headers)
    repos = repos_response.json()
    
    if not repos:
        print(" No repositories found")
        return
    
    print(f"✅ Found {len(repos)} repositories\n")
    
    # Step 3: Test Oracle on each completed repository
    for repo in repos:
        if repo['status'] != 'completed':
            print(f"⏭️  Skipping {repo['name']} (status: {repo['status']})")
            continue
        
        print(f"\n{'='*60}")
        print(f"🔍 Testing Oracle on: {repo['owner']}/{repo['name']}")
        print(f"{'='*60}\n")
        
        risk_response = requests.get(
            f"{API_URL}/analytics/repositories/{repo['id']}/risk-prediction",
            headers=headers
        )
        
        if risk_response.status_code != 200:
            print(f" Failed: {risk_response.text}")
            continue
        
        predictions = risk_response.json()
        
        if not predictions:
            print("ℹ️  No predictions available (not enough data)")
            continue
        
        print(f"✅ AI analyzed {len(predictions)} files\n")
        
        # Show top 5 predictions
        print(" Top 5 At-Risk Files:")
        print("-" * 60)
        
        for i, pred in enumerate(predictions[:5], 1):
            emoji = "🔴" if pred['risk_level'] == 'critical' else "🟠" if pred['risk_level'] == 'warning' else "🟡"
            file_name = pred['file_path'].split('/')[-1]
            
            print(f"\n{i}. {emoji} {file_name}")
            print(f"   Path: {pred['file_path']}")
            print(f"   Risk Score: {pred['risk_score']:.1f}%")
            print(f"   Level: {pred['risk_level'].upper()}")
            print(f"   Reason: {pred['reason']}")
            print(f"   Metrics: Churn={pred['churn']}, Complexity={pred['complexity']}, Authors={pred['author_count']}")
        
        print("\n" + "="*60)
        print(f"📊 Risk Summary:")
        critical = len([p for p in predictions if p['risk_level'] == 'critical'])
        warning = len([p for p in predictions if p['risk_level'] == 'warning'])
        watchlist = len([p for p in predictions if p['risk_level'] == 'watchlist'])
        print(f"   🔴 Critical: {critical}")
        print(f"   🟠 Warning: {warning}")
        print(f"   🟡 Watchlist: {watchlist}")
        print("="*60)

if __name__ == "__main__":
    try:
        test_oracle()
    except requests.exceptions.ConnectionError:
        print(" Could not connect to API. Make sure docker-compose is running.")
    except Exception as e:
        print(f" Error: {e}")
