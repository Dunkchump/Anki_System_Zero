

import asyncio
import hashlib
import os
import re
import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import edge_tts
import genanki
import pandas as pd
import requests

# --- CONFIGURATION ---
@dataclass
class Config:
    MODEL_ID: int = 1607392340
    DECK_ID: int = 2059400110
    DECK_NAME: str = "🇩🇪 German: System Zero (Academic)"
    CONCURRENCY: int = 3
    RETRIES: int = 3
    TIMEOUT: int = 45
    MEDIA_DIR: str = "media"
    CSV_FILE: str = "vocabulary.csv"
    VOICE: str = "de-DE-KatjaNeural"

# --- TEMPLATES ---
class CardTemplates:
    """Holds all HTML/CSS assets to keep main logic clean."""
    
    CSS = """
    .card { font-family: 'Roboto', 'Segoe UI', sans-serif; font-size: 16px; line-height: 1.4; color: #333; background-color: #f4f6f8; }
    .card-container { background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; max-width: 600px; margin: 0 auto; text-align: left; padding-bottom: 15px; }
    .header-box { padding: 15px; text-align: center; color: white; font-weight: bold; }
    .bg-der { background-color: #3498db; } .bg-die { background-color: #e74c3c; } .bg-das { background-color: #2ecc71; } .bg-none { background-color: #34495e; }
    .word-main { font-size: 2.2em; text-shadow: 0 1px 3px rgba(0,0,0,0.3); margin: 0; }
    .word-meta { font-size: 0.85em; opacity: 0.9; margin-top: 5px; font-family: monospace; }
    .section { padding: 10px 20px; border-bottom: 1px solid #eee; }
    .label { font-size: 0.7em; text-transform: uppercase; color: #95a5a6; font-weight: 800; letter-spacing: 0.5px; display: block; margin-bottom: 5px; }
    .definition { font-size: 1.1em; font-weight: 500; color: #2c3e50; }
    .morph-pill { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.8em; background: #ecf0f1; color: #7f8c8d; font-weight: bold; margin-right: 5px; }
    .narrative { font-style: italic; color: #555; background: #fffcf0; padding: 8px; border-left: 3px solid #f1c40f; font-size: 0.95em; }
    .nuance-box { font-size: 0.9em; color: #e67e22; font-weight: bold; margin-bottom: 5px; }
    .context-list { font-size: 0.95em; margin-left: 10px; border-left: 2px solid #ddd; padding-left: 10px; }
    .context-trans { font-size: 0.85em; color: #7f8c8d; margin-top: 4px; display: block; font-style: italic;}
    .mnemonic-box { background: #f0f8ff; padding: 8px; border-radius: 6px; color: #2980b9; font-size: 0.9em; }
    .analogues-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 0.85em; color: #555; background: #fafafa; padding: 8px; border-radius: 6px; }
    .img-box { text-align: center; margin-top: 5px; }
    .img-box img { max-width: 100%; border-radius: 8px; max-height: 250px; object-fit: cover; }
    .cloze-bracket { color: #ccc; background: #eee; padding: 0 5px; border-radius: 4px; }
    .cloze-reveal { color: #e74c3c; font-weight: bold; }
    """

    FRONT_REC = """<div class="card-container"><div style="padding:40px 20px; text-align:center;"><div style="font-size:0.8em; color:#bbb; text-transform:uppercase;">DEUTSCH</div><div style="font-size:2.5em; font-weight:bold; color:#333; margin-top:10px;">{{TargetWord}}</div><div style="color:#aaa; margin-top:10px;">{{Part_of_Speech}}</div></div></div>"""
    
    BACK_REC = """
    <div class="card-container">
        <div class="header-box bg-{{Gender}}">
            <div class="word-main">{{TargetWord}}</div>
            <div class="word-meta">/{{IPA}}/ • {{Part_of_Speech}}</div>
        </div>
        <div class="section"><span class="label">MEANING</span><div class="definition">{{Meaning}}</div></div>
        <div class="section"><span class="label">MORPHOLOGY & ETYMOLOGY</span><div style="margin-bottom:5px;"><span class="morph-pill bg-{{Gender}}" style="color:white;">{{Gender}}</span><span class="morph-pill">{{Morphology}}</span></div><div class="narrative">{{Etymology}}</div></div>
        <div class="section"><span class="label">CONTEXT ({{Nuance}})</span><div class="context-list">{{ContextSentences}}</div><div class="context-trans">{{ContextTranslation}}</div></div>
        <div class="section"><span class="label">MEMORY HOOK</span><div class="mnemonic-box">🪝 {{Mnemonic}}</div></div>
        <div class="section"><span class="label">ANALOGUES</span><div class="analogues-grid">{{Analogues}}</div></div>
        <div class="section"><div class="img-box">{{Image}}</div></div>
        {{AudioWord}}
        <div style="text-align:center; padding:5px;"><a href="https://forvo.com/search/{{TargetWord}}/" style="font-size:0.8em; color:#999; text-decoration:none;">🔊 Check Forvo</a></div>
    </div>
    """

    FRONT_PROD = """<div class="card-container"><div style="padding:40px 20px; text-align:center;"><div style="font-size:0.8em; color:#bbb; text-transform:uppercase;">TRANSLATE</div><div style="font-size:1.8em; font-weight:bold; color:#2c3e50; margin-top:10px;">{{Meaning}}</div><div class="mnemonic-box" style="margin-top:20px;">Hint: {{Mnemonic}}</div></div></div>"""
    
    FRONT_LIST = """<div class="card-container"><div style="padding:50px 20px; text-align:center;"><div style="font-size:4em;">🎧</div><div style="margin-top:20px; color:#888;">Listen & Recognize</div>{{AudioWord}}</div></div>"""
    
    # Raw string for regex JS
    FRONT_CLOZE = r"""<div class="card-container"><div class="header-box bg-none"><div style="font-size:1.2em;">Complete the Context</div></div><div class="section" style="padding: 20px;"><div id="context-sentence" style="font-size:1.1em; line-height:1.6;">{{ContextSentences}}</div></div></div><script>var contextDiv=document.getElementById("context-sentence");if(contextDiv){var content=contextDiv.innerHTML;var re=/<b>(.*?)<\/b>/gi;contextDiv.innerHTML=content.replace(re,"<span class='cloze-bracket'>[...]</span>");}</script>"""


# --- CORE LOGIC ---
class AssetManager:
    """Handles downloading and generating media assets."""
    
    @staticmethod
    def get_path(filename: str) -> str:
        return os.path.join(Config.MEDIA_DIR, filename)

    @staticmethod
    def download_image(url: str, filename: str) -> bool:
        """Downloads image synchronously with retry logic."""
        if not url or len(url) < 5: 
            return False
            
        # Extract URL if embedded in HTML tag
        match = re.search(r'src="([^"]+)"', url)
        clean_url = match.group(1) if match else url
        path = AssetManager.get_path(filename)

        if os.path.exists(path):
            return True

        headers = {'User-Agent': 'Mozilla/5.0 SystemZero/1.0'}
        for attempt in range(Config.RETRIES):
            try:
                response = requests.get(clean_url, headers=headers, timeout=Config.TIMEOUT)
                if response.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    return True
                elif response.status_code == 429:
                    time.sleep(3 * (attempt + 1))  # Exponential backoff
            except Exception:
                pass
        return False

    @staticmethod
    async def generate_audio(text: str, filename: str) -> bool:
        """Generates audio using Edge-TTS with retry logic."""
        if not text or not text.strip():
            return False
            
        path = AssetManager.get_path(filename)
        if os.path.exists(path):
            return True

        for attempt in range(Config.RETRIES):
            try:
                communicate = edge_tts.Communicate(text, Config.VOICE)
                await communicate.save(path)
                return True
            except Exception as e:
                if attempt == Config.RETRIES - 1:
                    print(f"   ❌ Audio failed for {filename}: {e}")
                await asyncio.sleep(1)
        return False


class AnkiDeckBuilder:
    """Main orchestrator for deck generation."""
    
    def __init__(self):
        self._ensure_media_dir()
        self.model = self._create_model()
        self.deck = genanki.Deck(Config.DECK_ID, Config.DECK_NAME)
        self.media_files = []
        self.semaphore = asyncio.Semaphore(Config.CONCURRENCY)

    def _ensure_media_dir(self):
        if not os.path.exists(Config.MEDIA_DIR):
            os.makedirs(Config.MEDIA_DIR)

    def _create_model(self) -> genanki.Model:
        return genanki.Model(
            Config.MODEL_ID,
            'Polyglot Academic v8.5 Pro',
            fields=[
                {'name': 'TargetWord'}, {'name': 'Meaning'}, {'name': 'IPA'}, 
                {'name': 'Part_of_Speech'}, {'name': 'Gender'}, {'name': 'Morphology'}, 
                {'name': 'Nuance'}, {'name': 'ContextSentences'}, {'name': 'ContextTranslation'}, 
                {'name': 'Etymology'}, {'name': 'Mnemonic'}, {'name': 'Analogues'}, 
                {'name': 'Image'}, {'name': 'Tags'}, 
                {'name': 'AudioWord'}, {'name': 'AudioSentence'}, {'name': 'UUID'}
            ],
            templates=[
                {'name': '1. Recognition', 'qfmt': CardTemplates.FRONT_REC, 'afmt': CardTemplates.BACK_REC},
                {'name': '2. Production', 'qfmt': CardTemplates.FRONT_PROD, 'afmt': CardTemplates.BACK_REC},
                {'name': '3. Listening', 'qfmt': CardTemplates.FRONT_LIST, 'afmt': CardTemplates.BACK_REC},
                {'name': '4. Context Cloze', 'qfmt': CardTemplates.FRONT_CLOZE, 'afmt': CardTemplates.BACK_REC},
            ],
            css=CardTemplates.CSS
        )

    async def process_row(self, index: int, row: pd.Series, total: int):
        async with self.semaphore:
            try:
                # 1. Data Cleaning
                raw_word = str(row.get('TargetWord', '')).strip()
                if not raw_word: return

                clean_word = re.sub(r'^(der|die|das)\s+', '', raw_word, flags=re.IGNORECASE).strip()
                # Create deterministic UUID based on word + part of speech
                uuid = hashlib.md5((clean_word + str(row.get('Part_of_Speech', ''))).encode()).hexdigest()
                
                print(f"[{index+1}/{total}] 🔄 Processing: {clean_word}...")

                # 2. Asset Generation Paths
                files = {
                    'img': f"{uuid}.jpg",
                    'audio_word': f"{uuid}_word.mp3",
                    'audio_sent': f"{uuid}_sent.mp3"
                }

                # 3. Tasks
                img_url = str(row.get('Image', ''))
                # Prepare text for context audio (remove HTML tags)
                context_clean = str(row.get('ContextSentences', '')).replace('<b>', '').replace('</b>', '').replace('<br>', '. ')
                
                # Launch Async Tasks
                # Run sync image download in a thread to not block async loop
                img_task = asyncio.to_thread(AssetManager.download_image, img_url, files['img'])
                audio_word_task = AssetManager.generate_audio(raw_word, files['audio_word'])
                audio_sent_task = AssetManager.generate_audio(context_clean[:500], files['audio_sent'])

                results = await asyncio.gather(img_task, audio_word_task, audio_sent_task)
                has_img, has_audio_w, has_audio_s = results

                # 4. Prepare Fields
                img_html = f'<img src="{files["img"]}">' if has_img else ""
                
                # Add to media list only if file actually exists
                if has_img: self.media_files.append(AssetManager.get_path(files['img']))
                if has_audio_w: self.media_files.append(AssetManager.get_path(files['audio_word']))
                if has_audio_s: self.media_files.append(AssetManager.get_path(files['audio_sent']))

                # 5. Create Note
                note = genanki.Note(
                    model=self.model,
                    fields=[
                        str(row.get('TargetWord', '')), str(row.get('Meaning', '')), 
                        str(row.get('IPA', '')), str(row.get('Part_of_Speech', '')),
                        str(row.get('Gender', '')), str(row.get('Morphology', '')), 
                        str(row.get('Nuance','')), str(row.get('ContextSentences', '')), 
                        str(row.get('ContextTranslation', '')), str(row.get('Etymology', '')), 
                        str(row.get('Mnemonic','')), str(row.get('Analogues','')),
                        img_html, str(row.get('Tags', '')),
                        f"[sound:{files['audio_word']}]", f"[sound:{files['audio_sent']}]", 
                        uuid
                    ],
                    tags=str(row.get('Tags', '')).split(),
                    guid=uuid
                )
                self.deck.add_note(note)
                print(f"   ✅ Ready: {clean_word}")

                # Slight delay to prevent rate limits
                await asyncio.sleep(1.0)

            except Exception as e:
                print(f"⚠️ Error processing row {index}: {e}")

    def export_package(self, filename: str = "system_zero_academic.apkg"):
        # Deduplicate media files and verify existence
        valid_media = list(set([f for f in self.media_files if os.path.exists(f)]))
        
        package = genanki.Package(self.deck)
        package.media_files = valid_media
        package.write_to_file(filename)
        print(f"\n🏁 SUCCESS! Package created: {filename} ({len(self.deck.notes)} notes)")


async def main():
    if not os.path.exists(Config.CSV_FILE):
        print(f"❌ Error: {Config.CSV_FILE} not found!")
        return

    try:
        df = pd.read_csv(Config.CSV_FILE, sep='|', encoding='utf-8-sig')
        df = df.fillna('') # Handle empty cells
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    builder = AnkiDeckBuilder()
    total_rows = len(df)
    
    print(f"🚀 Starting Build Process for {total_rows} items...")
    
    tasks = [builder.process_row(i, row, total_rows) for i, row in df.iterrows()]
    await asyncio.gather(*tasks)
    
    builder.export_package()

if __name__ == "__main__":
    asyncio.run(main())