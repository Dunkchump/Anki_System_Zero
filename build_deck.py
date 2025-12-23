"""
System Zero: Automated Anki Deck Generator
------------------------------------------
Version: 17.0 (Smart Audio Toggle + Perfect UI)
"""

import asyncio
import hashlib
import os
import re
import time
import random
from dataclasses import dataclass

import edge_tts
import genanki
import pandas as pd
import requests

# --- CONFIGURATION ---
@dataclass
class Config:
    MODEL_ID: int = 1607392370  # Новий ID для оновлення логіки JS
    DECK_ID: int = 2059400110
    DECK_NAME: str = "🇩🇪 German: System Zero (Academic)"
    
    CONCURRENCY: int = 5
    RETRIES: int = 5
    TIMEOUT: int = 60
    MEDIA_DIR: str = "media"
    CSV_FILE: str = "vocabulary.csv"
    VOICE: str = "de-DE-KatjaNeural"

# --- TEMPLATES ---
class CardTemplates:
    CSS = """
    .card { 
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
        font-size: 16px; 
        line-height: 1.5; 
        color: #333; 
        background-color: #f4f6f9; 
        margin: 0; padding: 0;
    }
    
    .card-container { 
        background: #fff; 
        border-radius: 12px; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); 
        overflow: hidden; 
        max-width: 500px; 
        margin: 10px auto; 
        text-align: left; 
        padding-bottom: 15px; 
    }
    
    /* HEADER */
    .header-box { padding: 25px 20px; text-align: center; color: white; font-weight: bold; }
    .bg-der { background: linear-gradient(135deg, #2980b9, #3498db); } 
    .bg-die { background: linear-gradient(135deg, #c0392b, #e74c3c); } 
    .bg-das { background: linear-gradient(135deg, #27ae60, #2ecc71); } 
    .bg-none { background: linear-gradient(135deg, #34495e, #2c3e50); }
    
    .word-main { font-size: 2.5em; font-weight: 800; margin: 0; letter-spacing: -0.5px; line-height: 1.1; }
    .word-meta { font-size: 0.9em; opacity: 0.9; margin-top: 8px; font-family: monospace; }
    
    /* LABELS & SECTIONS */
    .section { padding: 15px 20px; border-bottom: 1px solid #f2f2f2; }
    .label { 
        font-size: 0.75em; 
        text-transform: uppercase; 
        color: #adb5bd; 
        font-weight: 800; 
        letter-spacing: 1.2px; 
        display: block; 
        margin-bottom: 8px; 
    }
    
    /* CONTENT */
    .definition { font-size: 1.1em; font-weight: 600; color: #212529; }
    
    .morph-pill { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.85em; background: #e9ecef; color: #495057; font-weight: bold; margin-right: 5px; }
    .narrative { font-style: italic; color: #555; background: #fff9db; padding: 12px; border-radius: 8px; font-size: 0.95em; margin-top: 8px; border-left: 3px solid #f1c40f; }
    
    /* CONTEXT FIXES */
    .nuance-sub {
        font-size: 0.95em;
        color: #6c757d;
        font-weight: 500;
        margin-bottom: 12px;
        line-height: 1.4;
    }
    .context-list { font-size: 1em; border-left: 3px solid #dee2e6; padding-left: 15px; margin-left: 5px; color: #343a40; }
    .context-trans { font-size: 0.9em; color: #868e96; margin-top: 10px; display: block; font-style: italic; }

    /* MNEMONIC FIX */
    .mnemonic-box { background: #e7f5ff; padding: 12px; border-radius: 8px; color: #1971c2; font-size: 0.95em; }

    /* IMAGE FIX: FULL WIDTH */
    .img-box { 
        width: 100%; 
        margin-top: 5px; 
        border-radius: 8px; 
        overflow: hidden; 
        display: flex; 
        justify-content: center; 
        background: #000;
    }
    .img-box img { 
        width: 100%; 
        height: auto; 
        object-fit: cover; 
        display: block; 
    }

    /* --- BUTTONS & FOOTER LAYOUT --- */
    
    /* Context Audio Button (Inline) */
    .btn-context {
        display: inline-block;
        background: white;
        border: 1px solid #ced4da;
        color: #495057;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        cursor: pointer;
        margin-top: 10px;
        text-align: center;
        transition: all 0.2s;
        user-select: none;
    }
    .btn-context:active { transform: scale(0.96); background: #f8f9fa; }

    /* Footer Row (Horizontal Plane) */
    .footer-controls {
        display: flex;
        justify-content: center; /* Center horizontally */
        align-items: center;     /* Center vertically */
        gap: 15px;               /* Space between buttons */
        padding: 15px 20px;
        background: #f8f9fa;
        border-top: 1px solid #eee;
    }

    /* Style for Forvo Link */
    .btn-forvo {
        text-decoration: none;
        background: white;
        border: 1px solid #ced4da;
        color: #495057;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .native-audio {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    """

    FRONT_REC = """<div class="card-container"><div style="padding:50px 20px; text-align:center;"><div style="font-size:0.85em; color:#bbb; text-transform:uppercase; letter-spacing:1px; font-weight:bold;">DEUTSCH</div><div style="font-size:3em; font-weight:800; color:#2c3e50; margin-top:15px;">{{TargetWord}}</div><div style="color:#95a5a6; margin-top:10px; font-family:monospace;">{{Part_of_Speech}}</div></div></div>"""
    
    # Updated BACK_REC with Smart JS Toggle
    BACK_REC = """
    <div class="card-container">
        <div class="header-box bg-{{Gender}}">
            <div class="word-main">{{TargetWord}}</div>
            <div class="word-meta">/{{IPA}}/ • {{Part_of_Speech}}</div>
        </div>
        
        <div class="section">
            <span class="label">MEANING</span>
            <div class="definition">{{Meaning}}</div>
        </div>
        
        <div class="section">
            <span class="label">MORPHOLOGY & ETYMOLOGY</span>
            <div style="margin-bottom:10px;">
                <span class="morph-pill bg-{{Gender}}" style="color:white;">{{Gender}}</span>
                <span class="morph-pill">{{Morphology}}</span>
            </div>
            <div class="narrative">{{Etymology}}</div>
        </div>

        <div class="section">
            <span class="label">CONTEXT</span>
            {{#Nuance}}<div class="nuance-sub">{{Nuance}}</div>{{/Nuance}}
            
            <div class="context-list">{{ContextSentences}}</div>
            
            <div style="text-align:right;">
                <div class="btn-context" onclick="toggleContextAudio('{{AudioSentence}}', this)">
                    🎧 Listen
                </div>
            </div>
            
            <div class="context-trans">{{ContextTranslation}}</div>
        </div>

        <div class="section">
            <span class="label">MEMORY HOOK</span>
            <div class="mnemonic-box">💡 {{Mnemonic}}</div>
        </div>
        
        <div class="section">
            <span class="label">ANALOGUES</span>
            <div style="font-size:0.9em; color:#555;">{{Analogues}}</div>
        </div>
        
        {{#Image}}
        <div class="section" style="padding:0;"><div class="img-box">{{Image}}</div></div>
        {{/Image}}
        
        <div class="footer-controls">
            <a class="btn-forvo" href="https://forvo.com/search/{{TargetWord}}/">
                🔊 Forvo
            </a>
            <div class="native-audio">
                {{AudioWord}}
            </div>
        </div>
    </div>

    <script>
        // Global variable to track current audio instance
        if (typeof window.ctxAudio === 'undefined') {
            window.ctxAudio = null;
        }

        window.toggleContextAudio = function(filename, btn) {
            // Check if audio is currently playing
            if (window.ctxAudio && !window.ctxAudio.paused) {
                window.ctxAudio.pause();
                window.ctxAudio.currentTime = 0; // Reset to start
                btn.innerHTML = "🎧 Listen"; // Change text back
            } else {
                // If exists but paused, or doesn't exist, play new
                if (window.ctxAudio) { 
                     window.ctxAudio.pause(); 
                }
                window.ctxAudio = new Audio(filename);
                window.ctxAudio.play();
                btn.innerHTML = "⏹ Stop"; // Change text to Stop
                
                // Reset text when finished
                window.ctxAudio.onended = function() {
                    btn.innerHTML = "🎧 Listen";
                };
            }
        }
    </script>
    """

    FRONT_PROD = """<div class="card-container"><div style="padding:40px 20px; text-align:center;"><div style="font-size:0.8em; color:#bbb; text-transform:uppercase;">TRANSLATE</div><div style="font-size:1.8em; font-weight:bold; color:#2c3e50; margin-top:10px;">{{Meaning}}</div><div class="mnemonic-box" style="margin-top:20px;">Hint: {{Mnemonic}}</div></div></div>"""
    FRONT_LIST = """<div class="card-container"><div style="padding:50px 20px; text-align:center;"><div style="font-size:4em;">🎧</div><div style="margin-top:20px; color:#888;">Listen & Recognize</div>{{AudioWord}}</div></div>"""
    FRONT_CLOZE = r"""<div class="card-container"><div class="header-box bg-none"><div style="font-size:1.2em;">Complete the Context</div></div><div class="section" style="padding: 20px;"><div id="context-sentence" style="font-size:1.1em; line-height:1.6;">{{ContextSentences}}</div></div></div><script>var contextDiv=document.getElementById("context-sentence");if(contextDiv){var content=contextDiv.innerHTML;var re=/<b>(.*?)<\/b>/gi;contextDiv.innerHTML=content.replace(re,"<span class='cloze-bracket'>[...]</span>");}</script>"""


# --- ASSET MANAGER ---
class AssetManager:
    @staticmethod
    def get_path(filename: str) -> str:
        return os.path.join(Config.MEDIA_DIR, filename)

    @staticmethod
    def download_image(url: str, filename: str) -> bool:
        if not url or len(url) < 5: 
            return False
            
        match = re.search(r'src="([^"]+)"', url)
        clean_url = match.group(1) if match else url
        path = AssetManager.get_path(filename)

        if os.path.exists(path):
            return True

        headers = {'User-Agent': 'Mozilla/5.0'}
        for attempt in range(Config.RETRIES):
            try:
                response = requests.get(clean_url, headers=headers, timeout=Config.TIMEOUT)
                if response.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    return True
                elif response.status_code == 429:
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 2.0)
                    print(f"   ⏳ 429 Rate Limit. Sleeping {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    time.sleep(1)
            except Exception:
                time.sleep(1)
        return False

    @staticmethod
    async def generate_audio(text: str, filename: str) -> bool:
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
                await asyncio.sleep(1 + random.uniform(0.1, 1.0))
        return False


# --- DECK BUILDER ---
class AnkiDeckBuilder:
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
            'Polyglot Academic v17.0',
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
            await asyncio.sleep(random.uniform(0.1, 1.5))
            
            try:
                raw_word = str(row.get('TargetWord', '')).strip()
                if not raw_word: return

                clean_word = re.sub(r'^(der|die|das)\s+', '', raw_word, flags=re.IGNORECASE).strip()
                uuid = hashlib.md5((clean_word + str(row.get('Part_of_Speech', ''))).encode()).hexdigest()
                
                print(f"[{index+1}/{total}] 🔄 Processing: {clean_word}...")

                files = {
                    'img': f"{uuid}.jpg",
                    'audio_word': f"{uuid}_word.mp3",
                    'audio_sent': f"{uuid}_sent.mp3"
                }

                img_url = str(row.get('Image', ''))
                context_clean = str(row.get('ContextSentences', '')).replace('<b>', '').replace('</b>', '').replace('<br>', '. ')
                
                img_task = asyncio.to_thread(AssetManager.download_image, img_url, files['img'])
                audio_word_task = AssetManager.generate_audio(raw_word, files['audio_word'])
                audio_sent_task = AssetManager.generate_audio(context_clean[:500], files['audio_sent'])

                results = await asyncio.gather(img_task, audio_word_task, audio_sent_task)
                has_img, has_audio_w, has_audio_s = results

                if not has_img and len(img_url) > 5:
                    print(f"   ⚠️ Image skipped (download failed): {clean_word}")

                img_html = f'<img src="{files["img"]}">' if has_img else ""
                
                if has_img: self.media_files.append(AssetManager.get_path(files['img']))
                if has_audio_w: self.media_files.append(AssetManager.get_path(files['audio_word']))
                if has_audio_s: self.media_files.append(AssetManager.get_path(files['audio_sent']))

                audio_word_field = f"[sound:{files['audio_word']}]" if has_audio_w else ""
                audio_sent_field = files['audio_sent'] if has_audio_s else ""

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
                        audio_word_field, audio_sent_field, 
                        uuid
                    ],
                    tags=str(row.get('Tags', '')).split(),
                    guid=uuid
                )
                self.deck.add_note(note)
                print(f"   ✅ Ready: {clean_word}")

            except Exception as e:
                print(f"⚠️ Error processing row {index}: {e}")

    def export_package(self, filename: str = "system_zero_academic.apkg"):
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
        df = df.fillna('')
        print("🎲 Shuffling words...")
        df = df.sample(frac=1).reset_index(drop=True)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    builder = AnkiDeckBuilder()
    total_rows = len(df)
    
    print(f"🚀 Starting Build Process ({Config.CONCURRENCY} threads) for {total_rows} items...")
    tasks = [builder.process_row(i, row, total_rows) for i, row in df.iterrows()]
    await asyncio.gather(*tasks)
    
    builder.export_package()

if __name__ == "__main__":
    asyncio.run(main())