import urllib.request
import re

urls = [
    'https://www.runninghub.ai/pt-br/workflow/2119239526823604226',
    'https://www.runninghub.ai/pt-br/workflow/2119239626330701825',
    'https://www.runninghub.ai/pt-br/post/2043812317204320257',
    'https://www.runninghub.ai/pt-br/post/2050212088202711042'
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            title_m = re.search(r'<title>(.*?)</title>', html, re.I)
            title = title_m.group(1) if title_m else 'No title'
            
            # Look for JSON payload in next.js or runninghub react state
            workflow_name = ''
            wf_match = re.search(r'"workflowName"\s*:\s*"([^"]+)"', html)
            if wf_match:
                workflow_name = wf_match.group(1)
            
            desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', html)
            desc = desc_match.group(1) if desc_match else ''
            
            author_match = re.search(r'"authorName"\s*:\s*"([^"]+)"', html)
            author = author_match.group(1) if author_match else ''

            print(f'=== URL: {u} ===')
            print(f'TITLE: {title.strip()}')
            if workflow_name:
                print(f'WORKFLOW NAME: {workflow_name}')
            if author:
                print(f'AUTHOR: {author}')
            if desc:
                print(f'DESC: {desc[:250]}')
            
            # Look for node keywords or keywords in html
            keywords = ['MMAudio', 'Foley', 'Sound', 'Audio', 'Music', 'CosyVoice', 'Wan', 'Veo', 'Suno', 'Stable Audio', 'Ace', 'TTS', 'V2A']
            found_kws = [k for k in keywords if k.lower() in html.lower()]
            print(f'MATCHED KEYWORDS: {found_kws}')
            print()
    except Exception as e:
        print(f'URL {u} failed: {e}\n')
