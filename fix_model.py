import re
path = '../SKillsync - Copy/engines/llm_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace model to llama-3.1-8b-instant and lower max_tokens to 4000
content = content.replace("model='llama-3.3-70b-versatile'", "model='llama-3.1-8b-instant'")
content = content.replace('model="llama-3.3-70b-versatile"', 'model="llama-3.1-8b-instant"')
content = content.replace('max_tokens=8000', 'max_tokens=4000')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Model switched to bypass rate limit.')
