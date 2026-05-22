import time, json, urllib.request
API_KEY = 'rnd_xYp8vlh02OldCYrmLXL7kk0fNy7l'
SERVICE_ID = 'srv-d7uok8beo5us73d7r14g'
url = f'https://api.render.com/v1/services/{SERVICE_ID}/deploys'
headers = {'Authorization': f'Bearer {API_KEY}'}

def get_deploys():
    req = urllib.request.Request(url)
    for k,v in headers.items(): req.add_header(k,v)
    with urllib.request.urlopen(req) as r:
        return json.load(r)

print('Polling deploys...')
for _ in range(40):
    data = get_deploys()
    if not data.get('value'):
        print('No deploys yet')
        time.sleep(2)
        continue
    latest = data['value'][0]['deploy']
    print('Latest deploy:', latest['id'], latest['status'])
    if latest['status'] not in ('building','started','queued'):
        print(json.dumps(latest, indent=2))
        break
    time.sleep(3)
else:
    print('Timed out polling deploys')
