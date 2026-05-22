import json
import urllib.request

API_KEY = "rnd_xYp8vlh02OldCYrmLXL7kk0fNy7l"
SERVICE_ID = "srv-d7uok8beo5us73d7r14g"
url = f"https://api.render.com/v1/services/{SERVICE_ID}"
body = {
    "serviceDetails": {
        "envSpecificDetails": {
            "buildCommand": "pip install --upgrade pip setuptools wheel && pip install -r requirements.txt"
        }
    }
}

data = json.dumps(body).encode('utf-8')
req = urllib.request.Request(url, data=data, method='PATCH')
req.add_header('Content-Type', 'application/json')
req.add_header('Authorization', f'Bearer {API_KEY}')

try:
    with urllib.request.urlopen(req) as resp:
        out = resp.read().decode('utf-8')
        print(out)
except urllib.error.HTTPError as e:
    print('HTTPError', e.code, e.read().decode())
except Exception as e:
    print('Error', e)
