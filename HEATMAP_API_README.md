# NSE Heatmap API

Professional REST API for real-time NSE market heatmap data.

## 🚀 Features

- **Always Headless** - Runs completely in background
- **RESTful API** - Clean, professional endpoints
- **Real-time Data** - Scrapes live NSE heatmap
- **Multiple Categories** - Broad Market, Sectoral, Thematic, Strategy
- **Thread-Safe** - Handles concurrent requests
- **CORS Enabled** - Ready for frontend integration

## 📡 API Endpoints

### 1. Health Check
```bash
GET /health
```

### 2. Get Categories
```bash
GET /categories
```
Returns all available categories (Broad Market, Sectoral, etc.)

### 3. Get Indices
```bash
GET /indices?category=broad-market
```
Returns all indices for a specific category.

**Parameters:**
- `category` - Category key: `broad-market`, `sectoral`, `thematic`, `strategy`

**Example Response:**
```json
{
  "success": true,
  "category": "broad-market",
  "category_name": "Broad Market Indices",
  "total": 21,
  "indices": [
    {
      "name": "NIFTY 50",
      "value": "26,046.95",
      "change": "0.57%"
    }
  ]
}
```

### 4. Get Heatmap
```bash
GET /heatmap?category=broad-market&index=NIFTY 50
```
Returns heatmap data with all stocks for the specified index.

**Parameters:**
- `category` - Category key
- `index` - Index name (e.g., "NIFTY 50", "NIFTY BANK")

**Example Response:**
```json
{
  "success": true,
  "data": {
    "index_name": "NIFTY 50",
    "category": "Broad Market Indices",
    "total_stocks": 50,
    "scrape_timestamp": "2025-12-13T14:30:00",
    "stocks": [
      {
        "symbol": "TATASTEEL",
        "price": "172.00",
        "change": "3.38%",
        "color": "rgb(0, 128, 0)"
      }
    ]
  }
}
```

## 🔧 Installation

1. Install dependencies:
```bash
pip install flask flask-cors selenium webdriver-manager requests
```

2. Start the API:
```bash
python heatmap_api.py
```

The API will start on `http://localhost:5001`

## 📝 Usage Examples

### Using cURL

```bash
# Get all categories
curl http://localhost:5001/categories

# Get indices for sectoral category
curl "http://localhost:5001/indices?category=sectoral"

# Get NIFTY 50 heatmap
curl "http://localhost:5001/heatmap?category=broad-market&index=NIFTY 50"

# Get NIFTY BANK heatmap
curl "http://localhost:5001/heatmap?category=sectoral&index=NIFTY BANK"
```

### Using Python

```python
import requests

# Get categories
response = requests.get("http://localhost:5001/categories")
categories = response.json()

# Get indices
response = requests.get(
    "http://localhost:5001/indices",
    params={"category": "broad-market"}
)
indices = response.json()

# Get heatmap
response = requests.get(
    "http://localhost:5001/heatmap",
    params={
        "category": "broad-market",
        "index": "NIFTY 50"
    }
)
heatmap = response.json()
```

### Using JavaScript (Fetch)

```javascript
// Get categories
fetch('http://localhost:5001/categories')
  .then(res => res.json())
  .then(data => console.log(data));

// Get heatmap
fetch('http://localhost:5001/heatmap?category=broad-market&index=NIFTY 50')
  .then(res => res.json())
  .then(data => console.log(data));
```

## 🧪 Testing

Run the test script:
```bash
python test_heatmap_api.py
```

## 🐳 Docker Deployment

Coming soon...

## 📊 Available Indices

### Broad Market Indices
- NIFTY 50
- NIFTY NEXT 50
- NIFTY MIDCAP 50
- NIFTY MIDCAP 100
- NIFTY MIDCAP 150
- NIFTY SMALLCAP 50
- And more...

### Sectoral Indices
- NIFTY BANK
- NIFTY IT
- NIFTY AUTO
- NIFTY PHARMA
- NIFTY METAL
- And more...

### Thematic & Strategy Indices
- Available via API

## ⚙️ Configuration

- **Port**: Default `5001` (change via `PORT` environment variable)
- **CORS**: Enabled for `localhost:3000` and `localhost:3001`
- **Driver**: Headless Chrome

## 🛡️ Error Handling

All endpoints return consistent error responses:
```json
{
  "success": false,
  "error": "Error message"
}
```

## 📞 Support

For issues or questions, check the API documentation at:
```
http://localhost:5001/
```

## 📄 License

MIT

