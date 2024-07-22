import xml.etree.ElementTree as ET
import html
import os
import re
import shutil
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, unquote
from pathlib import Path


# pip install requests beautifulsoup4 が必要

# WordPressのエクスポートファイルを解析し、記事のリストを返す
def parse_wordpress_export(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    channel = root.find('channel')
    return channel.findall('item')

# 指定されたURLからページのタイトルと説明を取得する
def get_link_info(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else url
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else ''
        return title, description
    except:
        return url, ''

# リンクカードのHTMLを生成する
def create_link_card(url):
    title, description = get_link_info(url)
    return f"""
    <div class="link-card">
        <a href="{url}" target="_blank" rel="noopener noreferrer">
            <div class="link-card-content">
                <h3>{html.escape(title)}</h3>
                <p>{html.escape(description[:100])}...</p>
            </div>
        </a>
    </div>
    """

# コンテンツ内の画像URLとリンクを処理する
def process_content(content, base_url):
    def replace_image_url(match):
        old_url = match.group(1)
        parsed_url = urlparse(unquote(old_url))
        file_path = parsed_url.path.lstrip('/').replace('assets/', '')
        new_url = f"images/{file_path}"
        print(f"Replacing image URL: {old_url} -> {new_url}")
        return f'src="{new_url}" class="content-image"'
    
    def replace_link(match):
        url = match.group(1)
        return create_link_card(url)
    
    # 画像URLの置換
    content = re.sub(r'src="((?:https?://[^"]+)|(?:/[^"]+))"', replace_image_url, content)
    # リンクをリンクカードに置換
    content = re.sub(r'<a href="(https?://[^"]+)">[^<]+</a>', replace_link, content)
    return content

# WordPress記事をHTMLに変換する
def convert_to_html(item, base_url):
    title = item.find('title').text
    content = item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text
    date = datetime.strptime(item.find('pubDate').text, '%a, %d %b %Y %H:%M:%S %z')
    
    processed_content = process_content(content, base_url)
    
    css = """
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .link-card { border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin: 10px 0; }
        .link-card a { text-decoration: none; color: inherit; }
        .link-card-content h3 { margin: 0 0 5px 0; color: #1a0dab; }
        .link-card-content p { margin: 0; font-size: 0.9em; color: #545454; }
        .content-image { max-width: 100%; height: auto; max-height: 400px; object-fit: contain; }
    </style>
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{html.escape(title)}</title>
        {css}
    </head>
    <body>
        <article>
            <h1>{html.escape(title)}</h1>
            <time datetime="{date.isoformat()}">{date.strftime('%Y年%m月%d日')}</time>
            <div class="content">
                {processed_content}
            </div>
        </article>
    </body>
    </html>
    """
    return html_content

# ファイル名から無効な文字を削除し、安全なファイル名にする
def sanitize_filename(filename):
    invalid_chars = r'[<>:"/\\|?*()]'
    sanitized = re.sub(invalid_chars, '_', filename)
    return sanitized[:255]

# HTMLコンテンツをファイルに保存する
def save_html(content, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved HTML file: {filename}")
    except OSError as e:
        print(f"Error saving file {filename}: {e}")

# 画像ファイルをソースディレクトリからターゲットディレクトリにコピーする
def copy_images(source_dir, target_dir):
    if not source_dir.exists():
        print(f"Error: Source image directory not found at {source_dir}")
        return

    if not target_dir.exists():
        target_dir.mkdir(parents=True)

    for file in source_dir.glob('*'):
        if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            shutil.copy2(file, target_dir)
            print(f"Copied image: {file.name} to {target_dir}")

# メイン処理
def main():
    # パスの設定
    script_dir = Path(__file__).parent.absolute()
    input_file = Path(r"C:\Develop\note\note-sonoty_hearts-1.xml")
    output_dir = script_dir / 'output'
    source_image_dir = Path(r"C:\Develop\note\assets")
    target_image_dir = output_dir / 'images'
    base_url = 'https://note.com'

    # 設定情報の表示
    print(f"Script directory: {script_dir}")
    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    print(f"Source image directory: {source_image_dir}")
    print(f"Target image directory: {target_image_dir}")

    # 入力ファイルの存在確認
    if not input_file.exists():
        print(f"Error: Input file not found at {input_file}")
        return

    # 出力ディレクトリの作成
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        print(f"Created output directory: {output_dir}")

    # WordPressエクスポートファイルの解析
    items = parse_wordpress_export(input_file)

    # 各記事をHTMLに変換して保存
    for item in items:
        title = item.find('title').text
        if title:
            safe_title = sanitize_filename(title)
            filename = output_dir / f"{safe_title}.html"
            html_content = convert_to_html(item, base_url)
            save_html(html_content, filename)

    # 画像ファイルのコピー
    copy_images(source_image_dir, target_image_dir)

    print("HTML files and images have been processed and copied successfully.")
    print(f"Please open the HTML files from the '{output_dir}' directory to view them correctly.")

if __name__ == "__main__":
    main()