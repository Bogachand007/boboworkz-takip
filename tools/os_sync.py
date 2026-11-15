#!/usr/bin/env python3
"""Sync the client tracking page (data.json) from a published Production OS page.

The OS embeds two JSON blocks when "Update client view" is pressed:
  - client-data : summary data (texts, scenes, shots, milestones, deliverables)
  - sync-data   : frames, alternates, cast and style images

Usage:
  python3 tools/os_sync.py plan  <os_index.html>   # update data.json, list missing assets in sbdl/urls.txt
  python3 tools/os_sync.py finish                  # move downloaded sbdl/img/*.png into assets/*.jpg
"""
import json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_ORIGIN = 'https://26e31168-f8fd-469f-8a92-7765a41d539e.frame.claudeusercontent.com'
BLOB = re.compile(r'([0-9a-f]{32})')


def block(html, name):
    m = re.search(r'<script type="application/json" id="%s">([\s\S]*?)</script>' % name, html)
    if not m:
        sys.exit('missing block: ' + name)
    return json.loads(m.group(1) or '{}')


def asset(u, need):
    if not u:
        return u
    m = BLOB.search(u)
    if not m:
        return u
    b = m.group(1)
    if not os.path.exists(os.path.join(ROOT, 'assets', b + '.jpg')):
        need.add(b)
    return 'assets/%s.jpg' % b


def plan(path):
    html = open(path, encoding='utf-8').read()
    cd, sd = block(html, 'client-data'), block(html, 'sync-data')
    if not sd.get('projects'):
        sys.exit('sync-data is empty: press "Update client view" in the OS first')
    data = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    need = set()
    for cp in cd.get('projects', []):
        sp = next((p for p in sd['projects'] if p['id'] == cp['id']), None)
        tp = next((p for p in data['projects'] if p['id'] == cp['id']), None)
        if tp is None:
            tp = {'id': cp['id'], 'prompts': [], 'budget': [], 'music': []}
            data['projects'].append(tp)
        for k, v in cp.items():
            if k not in ('shots',):
                tp[k] = v
        frames = {s['id']: s for s in (sp or {}).get('shots', [])}
        old = {s['id']: s for s in tp.get('shots', [])}
        shots = []
        for s in cp.get('shots', []):
            n = dict(old.get(s['id'], {}))
            n.update(s)
            f = frames.get(s['id'])
            if f:
                n['frame'] = asset(f.get('frame'), need)
                n['frameLabel'] = f.get('frameLabel', '')
                n['alts'] = [{'url': asset(a.get('url'), need), 'label': a.get('label', '')} for a in f.get('alts', [])]
            shots.append(n)
        tp['shots'] = shots
        if sp:
            tp['cast'] = [dict(c, img=asset(c.get('img'), need),
                               imgs=[dict(i, url=asset(i.get('url'), need)) for i in c.get('imgs', [])])
                          for c in sp.get('cast', [])]
            tp['style'] = [dict(s, url=asset(s.get('url'), need)) for s in sp.get('style', [])]
    data['publishedAt'] = int(time.time() * 1000)
    json.dump(data, open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    with open(os.path.join(ROOT, 'sbdl', 'urls.txt'), 'w') as f:
        for b in sorted(need):
            f.write('%s %s/_blob/%s\n' % (b, OS_ORIGIN, b))
    print('shots:', sum(len(p.get('shots', [])) for p in data['projects']), 'missing assets:', len(need))


def finish():
    from PIL import Image
    d = os.path.join(ROOT, 'sbdl', 'img')
    n = 0
    for fn in os.listdir(d) if os.path.isdir(d) else []:
        b = fn.split('.')[0]
        Image.open(os.path.join(d, fn)).convert('RGB').save(os.path.join(ROOT, 'assets', b + '.jpg'), quality=92)
        n += 1
    print('assets added:', n)


if __name__ == '__main__':
    if sys.argv[1:2] == ['plan']:
        plan(sys.argv[2])
    elif sys.argv[1:2] == ['finish']:
        finish()
    else:
        print(__doc__)
