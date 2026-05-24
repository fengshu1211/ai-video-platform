import json, re, urllib.request

url = "http://localhost:8000/api/content/scripts"
raw = urllib.request.urlopen(url).read().decode("utf-8", errors="replace")

# Check for surrogate escape patterns
surr = re.compile(r'\\u[dD][89aAbBcCdDeEfF][0-9a-fA-F]{2}')
matches = surr.findall(raw)
print(f"Surrogate escapes found: {len(matches)}")
if matches:
    print(f"Examples: {matches[:5]}")
    clean = surr.sub("", raw)
    try:
        data = json.loads(clean)
        print(f"After cleaning: {len(data)} scripts parsed OK")
    except Exception as e:
        print(f"Still broken: {e}")
else:
    try:
        json.loads(raw)
        print("JSON is valid!")
    except json.JSONDecodeError as e:
        print(f"JSON error at pos {e.pos}: {e.msg}")
        print(f"Context: {repr(raw[e.pos-20:e.pos+20])}")
