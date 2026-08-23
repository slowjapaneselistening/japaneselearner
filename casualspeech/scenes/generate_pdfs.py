import json
import os
import glob
import re
import asyncio
import sys
from playwright.async_api import async_playwright

# pypdfの最新仕様（PdfWriter / PdfReader）に準拠したインポート
try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfWriter, PdfReader

# qrcode / pillow の自動インストールとインポート
try:
    import qrcode
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode", "pillow"])
    import qrcode

from io import BytesIO
import base64

OUTPUT_DIR = "PDF_Outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_qr_base64(url_str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(url_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

CSS_STYLES = """
@page {
    size: A4;
    margin: 15mm 12mm;
    background-color: #fcfbf9;
}
* { box-sizing: border-box; }
body {
    font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
    margin: 0; padding: 0; color: #2c3e50; line-height: 1.5; font-size: 10pt;
    background-color: #fcfbf9;
}
.header {
    background-color: #34495e; color: #ffffff;
    padding: 15px 15mm;
    display: table; width: 100%;
}
.header-text {
    display: table-cell; vertical-align: middle; text-align: left;
}
.header h1 { margin: 0; font-size: 15pt; letter-spacing: 0.5px; }
.header p { margin: 4px 0 0 0; font-size: 9pt; color: #bdc3c7; }
.header-qr-cell {
    display: table-cell; vertical-align: middle; text-align: right; width: 60px;
}
.header-qr {
    width: 60px; height: 60px;
    background-color: #ffffff; padding: 3px; border-radius: 4px;
}
.section-title {
    font-size: 11.5pt; color: #2c3e50; border-left: 4px solid #3498db;
    padding-left: 8px; margin-top: 18px; margin-bottom: 8px; font-weight: bold;
    page-break-after: avoid;
}
.dialogue-table { display: table; width: 100%; margin-bottom: 20px; border-spacing: 0 5px; }
.dialogue-row { display: table-row; }
.speaker-cell {
    display: table-cell; width: 40px; font-weight: bold; vertical-align: top;
    padding: 5px 4px; border-radius: 4px; text-align: center; font-size: 9.5pt;
}
.sp1 { background-color: #e8f4f8; color: #2980b9; }
.sp2 { background-color: #f5f7f8; color: #7f8c8d; }
.text-cell { display: table-cell; padding: 5px 10px; vertical-align: top; }
.sp1-text { background-color: #f4fafd; border-radius: 4px; }
.sp2-text { background-color: #fafbfc; border-radius: 4px; }
.jp-text { font-size: 10pt; color: #1a252f; margin-bottom: 1px; }
.en-text, .sub-text { font-size: 8.5pt; color: #7f8c8d; }
.romaji-text { font-size: 8.5pt; color: #e67e22; font-style: italic; }
rt { font-size: 5.5pt; color: #555555; }
.vocab-table { display: table; width: 100%; border-collapse: collapse; margin-bottom: 15px; }
.vocab-row { display: table-row; }
.vocab-header {
    display: table-cell; background-color: #3498db; color: white;
    font-weight: bold; padding: 6px; text-align: left; font-size: 9pt; border: 1px solid #d6dbdf;
}
.vocab-cell {
    display: table-cell; padding: 6px; border: 1px solid #d6dbdf;
    font-size: 9pt; vertical-align: middle; background-color: #ffffff;
}
.vocab-expr { width: 40%; font-weight: bold; color: #2c3e50; }
.vocab-ctx { width: 60%; font-size: 8.5pt; color: #566573; }
"""

def clean_vocabulary_text(text):
    text_str = str(text).replace("\n", "<br>")
    text_str = re.sub(r"\([ぁ-んァ-ン]+\)", "", text_str)
    text_str = text_str.replace("↔", " vs ")
    return text_str

EXTENDED_CSS = CSS_STYLES + """
.pdf-page-block { page-break-before: always; }
.pdf-page-block:first-child { page-break-before: avoid; }
"""

async def process_all(qr_b64):
    search_pattern = os.path.join("Output_Job*", "final_sentences.json")
    target_files = glob.glob(search_pattern)
    
    if not target_files:
        print("指定のファイルが見つかりませんでした。")
        return
        
    print(f"合計 {len(target_files)} 件のフォルダから処理を開始します...\n")
    
    pattern_meta = [
        ("txt_en", "A_Text_Eng", "テキスト + 英訳"),
        ("txt_romaji", "B_Text_Romaji", "テキスト + ローマ字"),
        ("txt_en_romaji", "C_Text_Eng_Romaji", "テキスト + 英訳 + ローマ字"),
        ("txt_only", "D_Text_Only", "テキストのみ")
    ]

    temp_dir = "temp_pdf_parts"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_files_map = { "txt_en": [], "txt_romaji": [], "txt_en_romaji": [], "txt_only": [] }

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        def extract_job_number(filepath):
            folder_name = os.path.basename(os.path.dirname(filepath))
            match = re.search(r'\d+', folder_name)
            return int(match.group()) if match else 0

        sorted_target_files = sorted(target_files, key=extract_job_number)

        for index, file_path in enumerate(sorted_target_files):
            current_dir = os.path.dirname(file_path)
            job_name = os.path.basename(current_dir)
            
            title_file_path = os.path.join(current_dir, "scene_title.json")
            title_prefix = ""
            if os.path.exists(title_file_path):
                try:
                    with open(title_file_path, "r", encoding="utf-8-sig") as tf:
                        title_data = json.load(tf)
                        t_ja = title_data.get("title_ja", "").strip()
                        t_en = title_data.get("title_en", "").strip()
                        if t_ja and t_en:
                            title_prefix = f"{t_ja}_{t_en}_"
                        elif t_ja:
                            title_prefix = f"{t_ja}_"
                        elif t_en:
                            title_prefix = f"{t_en}_"
                except Exception as e:
                    print(f"警告: {title_file_path} の読み込みに失敗しました。詳細: {e}")

            with open(file_path, "r", encoding="utf-8-sig") as f:
                raw_text = f.read().strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                try:
                    json_data = json.loads(raw_text)
                except json.JSONDecodeError as e:
                    print(f"エラー: {file_path} のJSONパースに失敗しました。詳細: {e}")
                    continue
            
            for p_type, sub_dir, sub_title in pattern_meta:
                html_body = ""
                for item in json_data:
                    sp_id = str(item.get("speaker", "1"))
                    sp_cls = "sp1" if sp_id == "1" else "sp2"
                    sp_name = "A" if sp_id == "1" else "B"
                    
                    extra_content = ""
                    if p_type == "txt_en":
                        extra_content = f'<div class="en-text">{item.get("exampleEn", "")}</div>'
                    elif p_type == "txt_romaji":
                        extra_content = f'<div class="romaji-text">{item.get("exampleRomaji", "")}</div>'
                    elif p_type == "txt_en_romaji":
                        extra_content = f'<div class="romaji-text">{item.get("exampleRomaji", "")}</div><div class="sub-text">{item.get("exampleEn", "")}</div>'
                        
                    html_body += f"""
                    <div class="dialogue-row">
                        <div class="speaker-cell {sp_cls}">{sp_name}</div>
                        <div class="text-cell {sp_cls}-text">
                            <div class="jp-text">{item.get('japaneseFurigana', '')}</div>
                            {extra_content}
                        </div>
                    </div>
                    """
                    
                vocab_html = ""
                for item in json_data:
                    if item.get("grammar2") and str(item["grammar2"]).strip():
                        expr_clean = clean_vocabulary_text(item["grammar2"])
                        vocab_html += f"""
                        <div class="vocab-row">
                            <div class="vocab-cell vocab-expr">{expr_clean}</div>
                            <div class="vocab-cell vocab-ctx">{item.get("japaneseFurigana", "")}</div>
                        </div>
                        """
                
                single_job_html = f"""
                <!DOCTYPE html>
                <html lang="ja">
                <head>
                    <meta charset="UTF-8">
                    <style>{EXTENDED_CSS}</style>
                </head>
                <body>
                    <div class="pdf-page-block">
                        <div class="header">
                            <div class="header-text">
                                <h1>日本語会話学習シート (Slow Japanese Listening)</h1>
                                <p>[ {title_prefix}{job_name} ] {sub_title}</p>
                            </div>
                            <div class="header-qr-cell">
                                <img src="data:image/png;base64,{qr_b64}" class="header-qr">
                            </div>
                        </div>
                        <div class="section-title">1. 会話 (Dialogue)</div>
                        <div class="dialogue-table">{html_body}</div>
                        <div class="section-title">2. 重要語彙・表現 (Vocabulary & Expressions)</div>
                        <div class="vocab-table">
                            <div class="vocab-row">
                                <div class="vocab-header">意味・解説 (Meaning & Notes)</div>
                                <div class="vocab-header">例文・会話文 (Context)</div>
                            </div>
                            {vocab_html}
                        </div>
                    </div>
                </body>
                </html>
                """
                
                temp_pdf_path = os.path.join(temp_dir, f"temp_{p_type}_{index}.pdf")
                await page.set_content(single_job_html)
                await page.pdf(
                    path=temp_pdf_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"}
                )
                temp_files_map[p_type].append(temp_pdf_path)

            print(f"個別PDF生成完了: {job_name}")

        await browser.close()

    print("\n[結合処理] 各JOBのPDFファイルを1本に統合しています...")
    def clean_filename(name):
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    for p_type, sub_dir, sub_title in pattern_meta:
        if not temp_files_map[p_type]:
            continue
            
        writer = PdfWriter()
        for temp_pdf in temp_files_map[p_type]:
            reader = PdfReader(temp_pdf)
            for page_data in reader.pages:
                writer.add_page(page_data)
            
        combined_filename = clean_filename(f"Combined_{sub_dir}.pdf")
        combined_output_filepath = os.path.join(OUTPUT_DIR, combined_filename)
        
        with open(combined_output_filepath, "wb") as f_out:
            writer.write(f_out)
        writer.close()
        print(f"Generated Combined PDF: {combined_output_filepath}")

    print("\n一時ファイルのクリーンアップ中...")
    for p_type, files in temp_files_map.items():
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

    print("\nすべての処理が正常に完了しました。")

if __name__ == "__main__":
    target_url = ""
    while not target_url:
        target_url = input("ヘッダーに埋め込むURLを入力してください: ").strip()
        if not target_url:
            print("エラー: URLが入力されていません。もう一度入力してください。")
    
    qr_b64 = generate_qr_base64(target_url)
    asyncio.run(process_all(qr_b64))