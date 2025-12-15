"""
Test Heatmap API
================

Test script for the NSE Heatmap API.

Usage:
    python test_heatmap_api.py
"""

import requests
import json

BASE_URL = "http://localhost:5001"


def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 80)
    print("Testing Health")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_categories():
    """Test categories endpoint"""
    print("\n" + "=" * 80)
    print("Testing Categories")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/categories")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total Categories: {data['total']}")
    
    for cat in data['categories']:
        print(f"\n  • {cat['key']}")
        print(f"    Name: {cat['name']}")
        print(f"    Description: {cat['description']}")


def test_indices():
    """Test indices endpoint"""
    print("\n" + "=" * 80)
    print("Testing Indices (Broad Market)")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/indices?category=broad-market", timeout=30)
    data = response.json()
    
    print(f"Status: {response.status_code}")
    
    if data['success']:
        print(f"Category: {data['category_name']}")
        print(f"Total Indices: {data['total']}")
        print(f"\nIndices:")
        for idx in data['indices'][:10]:
            print(f"  • {idx['name']} - {idx['value']} ({idx['change']})")
    else:
        print(f"Error: {data['error']}")


def test_heatmap():
    """Test heatmap endpoint"""
    print("\n" + "=" * 80)
    print("Testing Heatmap (NIFTY 50)")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/heatmap",
        params={'category': 'broad-market', 'index': 'NIFTY 50'},
        timeout=60
    )
    data = response.json()
    
    print(f"Status: {response.status_code}")
    
    if data['success']:
        heatmap = data['data']
        print(f"\nIndex: {heatmap['index_name']}")
        print(f"Category: {heatmap['category']}")
        print(f"Total Stocks: {heatmap['total_stocks']}")
        print(f"Scraped: {heatmap['scrape_timestamp']}")
        print(f"\nTop 10 Stocks:")
        for stock in heatmap['stocks'][:10]:
            print(f"  • {stock['symbol']}: {stock['price']} ({stock['change']})")
    else:
        print(f"Error: {data['error']}")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("NSE HEATMAP API - TEST CLIENT")
    print("=" * 80)
    
    try:
        test_health()
        test_categories()
        test_indices()
        test_heatmap()
        
        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("Make sure the API is running: python heatmap_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()

