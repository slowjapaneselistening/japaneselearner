import os
import re
import subprocess
from bs4 import BeautifulSoup

def get_git_file_mtime(filepath):
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct', filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        timestamp = result.stdout.strip()
        if timestamp:
            return int(timestamp)
    except Exception:
        pass
    return os.path.getmtime(filepath)

def extract_youtube_id(soup_or_text):
    match = re.search(r'(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/)([a-zA-Z0-9_-]{11})', str(soup_or_text))
    return match.group(1) if match else None

def scan_lessons():
    lessons = []
    for root, dirs, files in os.walk('.'):
        if root.startswith('./.git') or root.startswith('./.github') or root == '.':
            continue
        
        if 'index.html' in files:
            file_path = os.path.join(root, 'index.html')
            relative_path = os.path.relpath(file_path, '.').replace('\\', '/')
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            title_tag = soup.find('title')
            h1_tag = soup.find('h1')
            h2_tag = soup.find('h2')
            
            if title_tag and title_tag.text.strip():
                title = title_tag.text.strip()
            elif h1_tag and h1_tag.text.strip():
                title = h1_tag.text.strip()
            elif h2_tag and h2_tag.text.strip():
                title = h2_tag.text.strip()
            else:
                title = os.path.basename(os.path.dirname(relative_path))

            youtube_id = extract_youtube_id(content)
            mtime = get_git_file_mtime(file_path)

            lessons.append({
                'title': title,
                'path': relative_path,
                'youtube_id': youtube_id,
                'mtime': mtime
            })

    lessons.sort(key=lambda x: x['mtime'], reverse=True)
    return lessons

def generate_html(lessons):
    cards_html = ""
    for item in lessons:
        if item['youtube_id']:
            thumb_url = f"https://img.youtube.com/vi/{item['youtube_id']}/hqdefault.jpg"
        else:
            thumb_url = "https://via.placeholder.com/640x360?text=Japanese+Learning"

        cards_html += f'''
        <a href="{item['path']}" class="card">
            <div class="thumb-wrapper">
                <img src="{thumb_url}" alt="{item['title']}" loading="lazy">
                <div class="play-btn">▶</div>
            </div>
            <div class="card-body">
                <h3>{item['title']}</h3>
                <span class="btn-link">学習をはじめる →</span>
            </div>
        </a>
        '''

    html_content = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日本語 Learning Portal</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-sub: #64748b;
            --accent: #2563eb;
            --accent-hover: #1d4ed8;
            --radius: 12px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.5;
            padding-bottom: 60px;
        }}
        header {{
            background-color: var(--card-bg);
            border-bottom: 1px solid #e2e8f0;
            padding: 24px 20px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        header h1 {{ font-size: 1.6rem; color: var(--text-main); font-weight: 700; }}
        header p {{ font-size: 0.95rem; color: var(--text-sub); margin-top: 6px; }}
        
        main {{
            max-width: 1200px;
            margin: 32px auto 0;
            padding: 0 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            overflow: hidden;
            text-decoration: none;
            color: inherit;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: flex;
            flex-direction: column;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
        }}
        .thumb-wrapper {{
            position: relative;
            width: 100%;
            padding-top: 56.25%;
            background-color: #000;
        }}
        .thumb-wrapper img {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            object-fit: cover;
        }}
        .play-btn {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 44px; height: 44px;
            background: rgba(0,0,0,0.7);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            padding-left: 3px;
            transition: background 0.2s ease;
        }}
        .card:hover .play-btn {{ background: var(--accent); }}
        .card-body {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            justify-content: space-between;
        }}
        .card-body h3 {{
            font-size: 1rem;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .btn-link {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--accent);
        }}
    </style>
</head>
<body>
    <header>
        <h1>日本語 Learning Portal</h1>
        <p>最新のリスニング教材・クイズ一覧</p>
    </header>
    <main>
        <div class="grid">
            {cards_html}
        </div>
    </main>
</body>
</html>
'''
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == '__main__':
    lessons = scan_lessons()
    generate_html(lessons)