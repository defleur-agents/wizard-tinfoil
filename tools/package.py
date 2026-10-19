"""Re-embed app/ + web/ + openapi.json into the inline compose recipe and pin the image. Run after every source edit.
Usage: python3 tools/package.py <image-ref-with-digest>. Plain text replacement: every other compose line stays byte-identical."""
import base64, json, re, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
compose = root / 'runtipi' / 'docker-compose.yml'
text = compose.read_text()
m = re.search(r"b64decode\('([^']+)'\)", text)
if not m: sys.exit('inline blob not found; template changed')
old = json.loads(base64.b64decode(m.group(1)))
files = {name: (root / name).read_text() for name in old}
blob = base64.b64encode(json.dumps(files).encode()).decode()
text = text[:m.start(1)] + blob + text[m.end(1):]
if len(sys.argv) > 1:
    text, n = re.subn(r'(?m)^(    image: )127\.0\.0\.1:5000/wizard-tinfoil:\S+$', r'\g<1>' + sys.argv[1], text)
    if n != 1: sys.exit('image line not found')
compose.write_text(text)
print('embedded', ', '.join(files), '->', compose)
