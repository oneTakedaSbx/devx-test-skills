import urllib.request, json, re, sys, os
from datetime import datetime, timezone

# prefer explicit argv, fall back to env var so the PAT never needs to be pasted in chat
PAT   = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN', '')
if not PAT:
    sys.exit('ERROR: GITHUB_PERSONAL_ACCESS_TOKEN not set and no PAT supplied as argument')
OWNER = sys.argv[2]
REPO  = sys.argv[3]
SINCE = sys.argv[4]
UNTIL = sys.argv[5]
BASE  = sys.argv[6] if len(sys.argv) > 6 else 'main'
ORG   = OWNER

HEADERS = {
    'Authorization': f'Bearer {PAT}',
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'onetakeda-rn-drafter',
}

def gh_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()), r.headers.get('Link', '')

def paginate(url):
    results, link = gh_get(url)
    while 'rel="next"' in link:
        next_url = re.search(r'<([^>]+)>;\s*rel="next"', link).group(1)
        page, link = gh_get(next_url)
        results += page
    return results

def is_member(username):
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f'https://api.github.com/orgs/{ORG}/members/{username}',
                headers=HEADERS
            )
        )
        return True
    except urllib.error.HTTPError:
        return False

def get_files(pr_number):
    return paginate(
        f'https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}/files?per_page=100'
    )

pulls_raw = paginate(
    f'https://api.github.com/repos/{OWNER}/{REPO}/pulls?state=closed&base={BASE}&per_page=100'
)

since_dt = datetime.fromisoformat(SINCE.replace('Z', '+00:00'))
until_dt = datetime.fromisoformat(UNTIL.replace('Z', '+00:00'))

prs = []
for pr in pulls_raw:
    if not pr.get('merged_at'):
        continue
    merged = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
    if since_dt <= merged <= until_dt:
        files = get_files(pr['number'])
        prs.append({
            'number':    pr['number'],
            'title':     pr['title'],
            'body':      pr.get('body') or '',
            'author':    pr['user']['login'],
            'mergedAt':  pr['merged_at'],
            'labels':    [l['name'] for l in pr.get('labels', [])],
            'milestone': (pr.get('milestone') or {}).get('title'),
            'files':     [{'path': f['filename'], 'status': f['status'],
                           'additions': f['additions'], 'deletions': f['deletions']}
                          for f in files],
            'orgMember': is_member(pr['user']['login']),
        })

print(json.dumps(prs, ensure_ascii=False))
