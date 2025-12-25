"""
System Zero: Automated Anki Deck Generator
------------------------------------------
Version: 61.0 (Fix: Split Analogues by <br> tags - Guaranteed Table Layout)
"""

import asyncio
import hashlib
import os
import re
import time
import random
import ssl
import html
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import edge_tts
import genanki
import pandas as pd
import aiohttp
from tqdm.asyncio import tqdm as atqdm

# --- 🌍 LANGUAGE SWITCHER ---
CURRENT_LANG = "EN"

# --- CONFIGURATION MAP ---
LANG_CONFIG = {
    "DE": {
        "deck_name": "🇩🇪 German new style",
        "voice": "de-DE-ConradNeural",
        "voice_id": "CONRAD",
        "label": "DEUTSCH",
        "strip_regex": r'^(der|die|das)\s+',
        "forvo_lang": "de",
        # !!! NEW ID to force update !!!
        "model_id": 1607393148 
    },
    "EN": {
        "deck_name": "🇬🇧 English: System Zero max",
        "voice": "en-GB-SoniaNeural",
        "voice_id": "SONIA",
        "label": "ENGLISH",
        "strip_regex": r'^(to|the|a|an)\s+',
        "forvo_lang": "en",
        # !!! NEW ID to force update !!!
        "model_id": 1607393149 
    }
}

@dataclass
class Config:
    settings = LANG_CONFIG.get(CURRENT_LANG, LANG_CONFIG["DE"])
    
    MODEL_ID: int = settings["model_id"]
    # !!! NEW DECK ID to force update !!!
    DECK_ID: int = 2059400400 if CURRENT_LANG == "EN" else 2059400410
    
    DECK_NAME: str = settings["deck_name"]
    VOICE: str = settings["voice"]
    VOICE_ID: str = settings["voice_id"]
    LABEL: str = settings["label"]
    STRIP_REGEX: str = settings["strip_regex"]
    FORVO_CODE: str = settings["forvo_lang"]
    
    CONFETTI_URL: str = "https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"
    
    CONCURRENCY: int = 4
    RETRIES: int = 5
    TIMEOUT: int = 60  # Увеличено для генерации изображений
    IMAGE_TIMEOUT: int = 90  # Отдельный таймаут для изображений
    MEDIA_DIR: str = "media"
    CSV_FILE: str = "vocabulary.csv"
    REQUEST_DELAY_MIN: float = 0.5  # Минимальная задержка между запросами
    REQUEST_DELAY_MAX: float = 3.5  # Максимальная задержка между запросами

# --- TEMPLATES ---
class CardTemplates:
    CSS = """
    .card { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.5; color: #333; background-color: #f4f6f9; margin: 0; padding: 0; }
    .card-container { background: #fff; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; max-width: 500px; margin: 10px auto; text-align: left; padding-bottom: 15px; position: relative; }
    
    .header-box { padding: 25px 20px; text-align: center; color: white !important; font-weight: bold; background-color: #34495e; }
    .bg-der { background: linear-gradient(135deg, #2980b9, #3498db); } 
    .bg-die { background: linear-gradient(135deg, #c0392b, #e74c3c); } 
    .bg-das { background: linear-gradient(135deg, #27ae60, #2ecc71); } 
    .bg-none { background: linear-gradient(135deg, #8e44ad, #9b59b6); } /* Фиолетовый для немецких слов без артиклей */
    .bg-en, .bg-noun { background: linear-gradient(135deg, #2c3e50, #4ca1af); }
    
    .word-main { font-size: 2.5em; font-weight: 800; margin: 0; letter-spacing: -0.5px; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .word-meta { font-size: 0.9em; opacity: 0.9; margin-top: 8px; font-family: monospace; }
    
    .section { padding: 12px 20px; border-bottom: 1px solid #f2f2f2; }
    .label { font-size: 0.7em; text-transform: uppercase; color: #adb5bd; font-weight: 800; letter-spacing: 1.2px; display: block; margin-bottom: 6px; }
    .definition { font-size: 1.1em; font-weight: 600; color: #212529; }
    
    .morph-pill { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 0.8em; background: #e9ecef; color: #495057; font-weight: bold; margin-right: 5px; }
    .section .morph-pill.bg-en { display: none; }
    
    /* NUANCE (Clean Grey) */
    .nuance-sub {
        font-size: 0.95em;
        color: #666;
        margin-bottom: 12px;
        line-height: 1.4;
        font-weight: 500;
    }

    /* ETYMOLOGY (Yellow Box) */
    .narrative {
        font-style: italic; color: #555; background: #fff9db; 
        padding: 12px; border-radius: 8px; font-size: 0.95em;
        margin-top: 10px; border-left: 4px solid #f1c40f; line-height: 1.5;
    }

    /* MEMORY HOOK & HINT (Blue Box) */
    .mnemonic-box {
        background-color: #e7f5ff; /* Light Blue Background */
        color: #1971c2;            /* Dark Blue Text */
        padding: 12px;
        border-radius: 8px;
        font-size: 0.95em;
        border-left: 4px solid #1971c2;
    }

    /* ANALOGUES TABLE (BULLETPROOF) */
    .analogues-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95em;
        margin-top: 5px;
    }
    .ana-row td {
        padding-bottom: 6px; /* Spacing between rows */
        vertical-align: top;
    }
    .ana-lang {
        text-align: right;
        font-weight: bold;
        color: #adb5bd;
        padding-right: 12px;
        border-right: 2px solid #e9ecef; /* The line */
        width: 35px; /* Fixed width prevents jumping */
        white-space: nowrap;
    }
    .ana-word {
        text-align: left;
        padding-left: 12px;
        color: #343a40;
    }

    .sentence-container {
        display: flex; justify-content: space-between; align-items: center;
        background-color: #f8f9fa; border-radius: 6px;
        padding: 6px 10px; margin-bottom: 6px; border-left: 3px solid #dee2e6;
    }
    .sentence-text { flex-grow: 1; margin-right: 10px; font-size: 0.9em; line-height: 1.35; color: #343a40; }
    
    .replay-btn {
        background: white; color: #495057; border: 1px solid #ced4da; 
        border-radius: 50%; width: 26px; height: 26px;
        font-size: 12px; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center;
        transition: all 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.05); user-select: none;
    }
    .replay-btn:active { background: #e9ecef; transform: scale(0.95); }
    
    .img-box { width: 100%; margin-top: 5px; border-radius: 8px; overflow: hidden; display: flex; justify-content: center; background: #000; }
    .img-box img { width: 100%; height: auto; object-fit: cover; display: block; }

    .footer-controls { 
        display: flex; justify-content: center; align-items: center; 
        gap: 15px; padding: 15px 20px; background: #f8f9fa; border-top: 1px solid #eee; 
    }
    
    .pill-btn {
        display: inline-flex; justify-content: center; align-items: center;
        width: 120px; height: 36px; box-sizing: border-box;
        text-decoration: none; background: white; border: 1px solid #ced4da; 
        color: #495057; border-radius: 20px; font-size: 0.85em; font-weight: 600; 
        cursor: pointer; transition: background 0.2s; padding: 0; margin: 0; font-family: inherit;
    }
    .pill-btn:hover { background: #f1f3f5; }
    .pill-btn:active { transform: translateY(1px); }

    .tags-footer { text-align: center; padding: 10px; font-size: 0.75em; color: #ced4da; }
    .tag-pill { display: inline-block; background: #f1f3f5; padding: 2px 8px; border-radius: 10px; margin: 0 2px; }
    
    .hidden-native-audio { display: none; }
    """

    FRONT_REC = """<div class="card-container"><div style="padding:50px 20px; text-align:center;"><div style="font-size:0.85em; color:#bbb; text-transform:uppercase;">__LABEL__</div><div style="font-size:3em; font-weight:800; color:#2c3e50; margin-top:15px;">{{TargetWord}}</div><div style="color:#95a5a6; margin-top:10px; font-family:monospace;">{{Part_of_Speech}}</div></div></div>"""
    
    JS_PLAYER = """
    <script>
    function toggleAudio(audioId, btn) {
        var audio = document.getElementById(audioId);
        if (!audio) return;
        if (!audio.paused) {
            audio.pause();
            btn.innerHTML = "▶";
        } else {
            document.querySelectorAll('audio').forEach(el => { el.pause(); el.currentTime = 0; });
            document.querySelectorAll('.replay-btn').forEach(b => b.innerHTML = "▶");
            audio.play();
            btn.innerHTML = "⏸";
        }
        audio.onended = function() { btn.innerHTML = "▶"; };
    }
    function playMainAudio() { var a = document.getElementById('main_word_audio'); if(a){a.currentTime=0; a.play();} }

    try {
        var count = 200;
        var defaults = { origin: { y: 0.7 } };
        function fire(particleRatio, opts) {
          confetti(Object.assign({}, defaults, opts, { particleCount: Math.floor(count * particleRatio) }));
        }
        setTimeout(function() {
            fire(0.25, { spread: 26, startVelocity: 55, });
            fire(0.2, { spread: 60, });
        }, 300);
    } catch (e) { console.log("Confetti err"); }
    </script>
    <script src="_confetti.js"></script>
    """

    BACK_REC = """
    <div class="card-container">
        <div class="header-box bg-{{Gender}}">
            <div class="word-main">{{TargetWord}}</div>
            <div class="word-meta">/{{IPA}}/ • {{Part_of_Speech}}</div>
        </div>
        
        <div class="section"><span class="label">MEANING</span><div class="definition">{{Meaning}}</div></div>
        
        <div class="section">
            <span class="label">MORPHOLOGY & ETYMOLOGY</span>
            <div style="margin-bottom:10px;">
                <span class="morph-pill bg-{{Gender}}" style="color:white;">{{Gender}}</span>
                {{#Morphology}}<span class="morph-pill">{{Morphology}}</span>{{/Morphology}}
            </div>
            {{#Etymology}}<div class="narrative">{{Etymology}}</div>{{/Etymology}}
        </div>

        <div class="section">
            <span class="label">CONTEXT</span>
            {{#Nuance}}<div class="nuance-sub">{{Nuance}}</div>{{/Nuance}}
            
            {{#Sentence_1}}
            <div class="sentence-container">
                <span class="sentence-text">{{Sentence_1}}</span>
                <button class="replay-btn" onclick="toggleAudio('audio_s1', this)">▶</button>
            </div>
            <audio id="audio_s1" src="{{Audio_Sent_1}}" preload="none"></audio>
            {{/Sentence_1}}

            {{#Sentence_2}}
            <div class="sentence-container">
                <span class="sentence-text">{{Sentence_2}}</span>
                <button class="replay-btn" onclick="toggleAudio('audio_s2', this)">▶</button>
            </div>
            <audio id="audio_s2" src="{{Audio_Sent_2}}" preload="none"></audio>
            {{/Sentence_2}}

            {{#Sentence_3}}
            <div class="sentence-container">
                <span class="sentence-text">{{Sentence_3}}</span>
                <button class="replay-btn" onclick="toggleAudio('audio_s3', this)">▶</button>
            </div>
            <audio id="audio_s3" src="{{Audio_Sent_3}}" preload="none"></audio>
            {{/Sentence_3}}
            
            <div style="font-size:0.8em; color:#aaa; font-style:italic; margin-top:15px; opacity: 0.8; line-height: 1.4;">
                {{ContextTranslation}}
            </div>
        </div>

        <div class="section"><span class="label">MEMORY HOOK</span><div class="mnemonic-box">💡 {{Mnemonic}}</div></div>

        {{#Analogues}}
        <div class="section">
            <span class="label">ANALOGUES</span>
            {{Analogues}}
        </div>
        {{/Analogues}}
        
        {{#Image}}<div class="section" style="padding:0;"><div class="img-box">{{Image}}</div></div>{{/Image}}
        
        <div class="footer-controls">
            <a class="pill-btn" href="https://forvo.com/word/{{TargetWord}}/#__FORVO__">🔊 Forvo</a>
            <button class="pill-btn" onclick="playMainAudio()">🎧 Listen</button>
        </div>
        
        <div class="tags-footer">{{#Tags}}<span class="tag-pill">{{Tags}}</span>{{/Tags}}</div>

        <div class="hidden-native-audio">{{AudioWord}}</div>
        <audio id="main_word_audio" src="{{Audio_Path_Word}}" preload="auto"></audio>
    </div>
    """ + JS_PLAYER
    
    # Blue Hint Box in Production Card
    FRONT_PROD = """<div class="card-container"><div style="padding:40px 20px; text-align:center;"><div style="font-size:0.8em; color:#bbb; text-transform:uppercase;">TRANSLATE</div><div style="font-size:1.8em; font-weight:bold; color:#2c3e50; margin-top:10px;">{{Meaning}}</div><div class="mnemonic-box" style="margin-top:20px;border-left: none">Hint: {{Mnemonic}}</div></div></div>"""
    FRONT_LIST = """<div class="card-container"><div style="padding:50px 20px; text-align:center;"><div style="font-size:4em;">🎧</div><div style="margin-top:20px; color:#888;">Listen & Recognize</div><div style="display:none;">{{AudioWord}}</div><button class="pill-btn" style="margin-top:20px; width:150px;" onclick="document.getElementById('q_audio').play()">▶ Play Again</button><audio id="q_audio" src="{{Audio_Path_Word}}" autoplay></audio></div></div>"""
    FRONT_CLOZE = r"""<div class="card-container"><div class="header-box bg-none"><div style="font-size:1.2em;">Complete the Context</div></div><div class="section" style="padding: 20px;"><div id="context-sentence" style="font-size:1.1em; line-height:1.6;">{{ContextSentences}}</div></div></div><script>var contextDiv=document.getElementById("context-sentence");if(contextDiv){var content=contextDiv.innerHTML;var re=/<b>(.*?)<\/b>/gi;contextDiv.innerHTML=content.replace(re,"<span style='color:#3498db; border-bottom:2px solid #3498db; font-weight:bold;'>[...]</span>");}</script>"""


# --- ASSET MANAGER ---
class AssetManager:
    @staticmethod
    def get_path(filename: str) -> str:
        return os.path.join(Config.MEDIA_DIR, filename)

    @staticmethod
    def extract_url_from_tag(raw_input: str) -> str:
        if not raw_input or str(raw_input).lower() == "nan": return ""
        match = re.search(r'src=["\']([^"\']+)["\']', str(raw_input))
        if match: return match.group(1)
        return str(raw_input).strip().strip('"').strip("'")

    @staticmethod
    async def download_file(raw_input: str, filename: str, builder=None) -> bool:
        """Загрузка файла с улучшенной обработкой и jitter для имитации пользователя"""
        url = AssetManager.extract_url_from_tag(raw_input)
        if not url or len(url) < 5: return False
        path = AssetManager.get_path(filename)
        if os.path.exists(path) and os.path.getsize(path) > 1000: return True
        
        # Реалистичные headers для имитации браузера
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://pollinations.ai/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        ssl_ctx = ssl.create_default_context(); ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE

        # Экспоненциальный backoff с jitter
        for attempt in range(Config.RETRIES):
            try:
                # Случайная задержка перед запросом (jitter для имитации пользователя)
                delay = random.uniform(Config.REQUEST_DELAY_MIN, Config.REQUEST_DELAY_MAX)
                await asyncio.sleep(delay)
                
                connector = aiohttp.TCPConnector(ssl=False)
                # Увеличенный таймаут для изображений
                timeout = aiohttp.ClientTimeout(total=Config.IMAGE_TIMEOUT)
                async with aiohttp.ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            if len(content) > 500:  # Проверка, что файл не пустой
                                with open(path, 'wb') as f: f.write(content)
                                if builder:
                                    builder._adjust_concurrency(status_code=200, is_success=True)
                                return True
                        else:
                            # Обработать статус 429 адаптивно
                            if response.status == 429 and builder:
                                builder._adjust_concurrency(status_code=429)
                            
                            # Экспоненциальный backoff: 2, 4, 8, 16, 32 секунд
                            backoff = 2 ** attempt
                            print(f"   ⚠️ Статус {response.status}, попытка {attempt+1}/{Config.RETRIES}, ожидание {backoff}с...")
                            await asyncio.sleep(backoff)
            except asyncio.TimeoutError:
                print(f"   ⏱️ Timeout при загрузке, попытка {attempt+1}/{Config.RETRIES}")
                if builder:
                    builder._adjust_concurrency(is_success=False)
                if attempt < Config.RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff
            except Exception as e:
                error_msg = str(e)[:50] if str(e) else "Unknown error"
                print(f"   ❌ Ошибка загрузки: {error_msg}, попытка {attempt+1}/{Config.RETRIES}")
                if builder:
                    builder._adjust_concurrency(is_success=False)
                if attempt < Config.RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
        
        print(f"   ✗ Не удалось загрузить: {filename}")
        return False

    @staticmethod
    def clean_audio_text(text: str) -> str:
        if not text: return ""
        text = html.unescape(str(text))
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'(^|\s)\d+[\.\)]\s*', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    async def generate_audio(text: str, filename: str, volume: str = "+0%") -> bool:
        if not text or not text.strip(): return False
        clean_text = AssetManager.clean_audio_text(text)
        path = AssetManager.get_path(filename)
        try:
            # Небольшая задержка перед TTS для избежания перегрузки
            await asyncio.sleep(random.uniform(0.1, 0.3))
            communicate = edge_tts.Communicate(clean_text, Config.VOICE, volume=volume)
            await communicate.save(path)
            return True
        except Exception as e: 
            return False

# --- DECK BUILDER ---
class AnkiDeckBuilder:
    CACHE_FILE = "build_cache.json"
    
    def __init__(self):
        self._ensure_media_dir()
        self.model = self._create_model()
        self.deck = genanki.Deck(Config.DECK_ID, Config.DECK_NAME)
        self.media_files = []
        self.semaphore = asyncio.Semaphore(Config.CONCURRENCY)
        self.current_concurrency = Config.CONCURRENCY
        self.cache = self._load_cache()
        self.stats = {
            'words_processed': 0,
            'images_success': 0,
            'images_failed': 0,
            'audio_word_success': 0,
            'audio_word_failed': 0,
            'audio_sent_success': 0,
            'audio_sent_failed': 0,
            'total_bytes': 0,
            'start_time': time.time()
        }
        # Адаптивна паралелізація
        self.adaptive_stats = {
            'consecutive_success': 0,
            'consecutive_failures': 0,
            'last_status_429': False,
            'concurrency_adjustments': 0
        }

    def _ensure_media_dir(self):
        if not os.path.exists(Config.MEDIA_DIR): os.makedirs(Config.MEDIA_DIR)

    def _load_cache(self) -> dict:
        """Завантажити кеш вже обробленних файлів"""
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Зберегти кеш"""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except:
            pass

    def _check_cache(self, filename: str) -> bool:
        """Перевірити, чи файл вже в кеші"""
        if filename not in self.cache:
            return False
        cache_time = self.cache[filename]
        file_path = AssetManager.get_path(filename)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 500:
            return True
        del self.cache[filename]
        return False

    def _update_cache(self, filename: str):
        """Додати файл до кеша"""
        self.cache[filename] = datetime.now().isoformat()
        self._save_cache()

    def _adjust_concurrency(self, status_code: int = None, is_success: bool = None):
        """Адаптивна зміна паралелізації залежно від статусу сервера"""
        if status_code == 429:  # Too Many Requests
            self.adaptive_stats['last_status_429'] = True
            self.adaptive_stats['consecutive_success'] = 0
            self.adaptive_stats['consecutive_failures'] += 1
            
            # Зменшити паралелізацію на 50%
            if self.current_concurrency > 1:
                old_concurrency = self.current_concurrency
                self.current_concurrency = max(1, int(self.current_concurrency * 0.5))
                if old_concurrency != self.current_concurrency:
                    self.semaphore = asyncio.Semaphore(self.current_concurrency)
                    self.adaptive_stats['concurrency_adjustments'] += 1
                    print(f"⚠️ 429 Too Many Requests! Паралелізація зменшена: {old_concurrency} → {self.current_concurrency}")
        
        elif status_code and status_code < 400:  # Успішний запит
            self.adaptive_stats['consecutive_failures'] = 0
            self.adaptive_stats['consecutive_success'] += 1
            
            # Якщо 5+ успіхів поспіль - спробувати подвоїти паралелізацію
            if (self.adaptive_stats['consecutive_success'] >= 5 and 
                self.current_concurrency < Config.CONCURRENCY * 2 and
                not self.adaptive_stats['last_status_429']):
                old_concurrency = self.current_concurrency
                self.current_concurrency = min(Config.CONCURRENCY * 2, self.current_concurrency * 2)
                if old_concurrency != self.current_concurrency:
                    self.semaphore = asyncio.Semaphore(self.current_concurrency)
                    self.adaptive_stats['concurrency_adjustments'] += 1
                    self.adaptive_stats['consecutive_success'] = 0
                    print(f"✅ Сервер швидкий! Паралелізація збільшена: {old_concurrency} → {self.current_concurrency}")
        
        elif is_success is False:  # Помилка завантаження
            self.adaptive_stats['consecutive_success'] = 0
            self.adaptive_stats['consecutive_failures'] += 1

    async def _download_confetti_lib(self):
        filename = "_confetti.js"
        if not os.path.exists(AssetManager.get_path(filename)):
            try: await AssetManager.download_file(Config.CONFETTI_URL, filename, self)
            except: pass
        if os.path.exists(AssetManager.get_path(filename)):
             self.media_files.append(AssetManager.get_path(filename))

    def _create_model(self) -> genanki.Model:
        front_rec_safe = CardTemplates.FRONT_REC.replace("__LABEL__", Config.LABEL)
        back_rec_safe = CardTemplates.BACK_REC.replace("__FORVO__", Config.FORVO_CODE)
        
        fields = [
            {'name': 'TargetWord'}, {'name': 'Meaning'}, {'name': 'IPA'}, {'name': 'Part_of_Speech'}, 
            {'name': 'Gender'}, {'name': 'Morphology'}, {'name': 'Nuance'}, 
            {'name': 'Sentence_1'}, {'name': 'Sentence_2'}, {'name': 'Sentence_3'},
            {'name': 'ContextTranslation'}, {'name': 'Etymology'}, {'name': 'Mnemonic'}, {'name': 'Analogues'}, 
            {'name': 'Image'}, {'name': 'Tags'}, 
            {'name': 'AudioWord'}, 
            {'name': 'Audio_Sent_1'}, {'name': 'Audio_Sent_2'}, {'name': 'Audio_Sent_3'},
            {'name': 'Audio_Path_Word'}, 
            {'name': 'ContextSentences'}, 
            {'name': 'UUID'}
        ]

        return genanki.Model(
            Config.MODEL_ID,
            f'System Zero {CURRENT_LANG} v61.0',
            fields=fields,
            templates=[
                {'name': '1. Recognition', 'qfmt': front_rec_safe, 'afmt': back_rec_safe},
                {'name': '2. Production', 'qfmt': CardTemplates.FRONT_PROD, 'afmt': back_rec_safe},
                {'name': '3. Listening', 'qfmt': CardTemplates.FRONT_LIST, 'afmt': back_rec_safe},
                {'name': '4. Context Cloze', 'qfmt': CardTemplates.FRONT_CLOZE, 'afmt': back_rec_safe},
            ],
            css=CardTemplates.CSS
        )

    def clean_translation(self, text: str) -> str:
        if not text: return ""
        lines = re.split(r'(<br>|\n)', str(text))
        cleaned_lines = []
        for line in lines:
            if line in ['<br>', '\n']:
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(re.sub(r'^\s*\d+[\.\)]\s*', '', line))
        return "".join(cleaned_lines)

    # --- FIXED: Use REGEX to split by <br> or newline ---
    def format_analogues_html(self, text: str) -> str:
        if not text or str(text).lower() == 'nan': return ""
        
        # THIS WAS THE FIX: Split by newline OR <br> tag
        lines = re.split(r'\n|<br\s*/?>', str(text))
        
        html_out = '<table class="analogues-table">'
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            parts = line.split(':', 1)
            if len(parts) == 2:
                code = parts[0].strip()
                word = parts[1].strip()
                html_out += f'<tr class="ana-row"><td class="ana-lang">{code}</td><td class="ana-word">{word}</td></tr>'
            else:
                html_out += f'<tr class="ana-row"><td colspan="2" class="ana-word">{line}</td></tr>'
        
        html_out += '</table>'
        return html_out

    async def process_row(self, index: int, row: pd.Series, total: int, pbar):
        await asyncio.sleep(random.uniform(0.05, 0.2))
        async with self.semaphore:
            try:
                raw_word = str(row.get('TargetWord', '')).strip()
                if not raw_word: 
                    pbar.update(1)
                    return

                clean_word = re.sub(Config.STRIP_REGEX, '', raw_word, flags=re.IGNORECASE).strip()
                base_hash = hashlib.md5((clean_word + str(row.get('Part_of_Speech', ''))).encode()).hexdigest()
                uuid = f"{base_hash}_{CURRENT_LANG}"
                
                self.stats['words_processed'] += 1
                print(f"[{index+1}/{total}] 🔄 Processing: {clean_word}...")

                raw_context = str(row.get('ContextSentences', ''))
                sentences = [s.strip() for s in re.split(r'<br>|\n', raw_context) if s.strip()]
                while len(sentences) < 3: sentences.append("")
                
                raw_translation = str(row.get('ContextTranslation', ''))
                clean_trans = self.clean_translation(raw_translation)

                # --- PROCESS ANALOGUES (FIXED) ---
                raw_analogues = str(row.get('Analogues', ''))
                clean_analogues = self.format_analogues_html(raw_analogues)

                cloze_context = raw_context
                if not cloze_context and sentences[0]: cloze_context = sentences[0]

                vid = Config.VOICE_ID
                f_img = f"_img_{uuid}.jpg"
                f_word = f"_word_{uuid}_{vid}_v54.mp3"
                f_s1 = f"_sent_1_{uuid}_{vid}_v54.mp3"
                f_s2 = f"_sent_2_{uuid}_{vid}_v54.mp3"
                f_s3 = f"_sent_3_{uuid}_{vid}_v54.mp3"

                tasks = []
                
                # Перевірити кеш для файлів
                if self._check_cache(f_img):
                    tasks.append(asyncio.sleep(0))  # Пропустити, вже є
                    has_img_cached = True
                else:
                    tasks.append(AssetManager.download_file(str(row.get('Image', '')), f_img, self))
                    has_img_cached = False
                
                if self._check_cache(f_word):
                    tasks.append(asyncio.sleep(0))
                    has_w_cached = True
                else:
                    tasks.append(AssetManager.generate_audio(raw_word, f_word, volume="+40%"))
                    has_w_cached = False
                
                tasks.append(AssetManager.generate_audio(sentences[0], f_s1, volume="+0%") if sentences[0] else asyncio.sleep(0))
                tasks.append(AssetManager.generate_audio(sentences[1], f_s2, volume="+0%") if sentences[1] else asyncio.sleep(0))
                tasks.append(AssetManager.generate_audio(sentences[2], f_s3, volume="+0%") if sentences[2] else asyncio.sleep(0))

                results = await asyncio.gather(*tasks)
                has_img, has_w, has_s1, has_s2, has_s3 = results
                
                # Оновити кеш і статистику
                if has_img or has_img_cached:
                    self.stats['images_success'] += 1
                    if has_img:
                        self._update_cache(f_img)
                else:
                    self.stats['images_failed'] += 1
                
                if has_w or has_w_cached:
                    self.stats['audio_word_success'] += 1
                    if has_w:
                        self._update_cache(f_word)
                else:
                    self.stats['audio_word_failed'] += 1
                
                if has_s1:
                    self.stats['audio_sent_success'] += 1
                    self._update_cache(f_s1)
                elif sentences[0]:
                    self.stats['audio_sent_failed'] += 1
                
                if has_s2:
                    self.stats['audio_sent_success'] += 1
                    self._update_cache(f_s2)
                elif sentences[1]:
                    self.stats['audio_sent_failed'] += 1
                
                if has_s3:
                    self.stats['audio_sent_success'] += 1
                    self._update_cache(f_s3)
                elif sentences[2]:
                    self.stats['audio_sent_failed'] += 1

                if has_img: self.media_files.append(AssetManager.get_path(f_img))
                if has_w: self.media_files.append(AssetManager.get_path(f_word))
                if has_s1: self.media_files.append(AssetManager.get_path(f_s1))
                if has_s2: self.media_files.append(AssetManager.get_path(f_s2))
                if has_s3: self.media_files.append(AssetManager.get_path(f_s3))

                gender = "en" if CURRENT_LANG == "EN" else str(row.get('Gender', '')).strip().lower()
                if not gender or gender == "nan": gender = "none"
                
                pbar.update(1)

                note = genanki.Note(
                    model=self.model,
                    fields=[
                        str(row.get('TargetWord', '')), str(row.get('Meaning', '')), str(row.get('IPA', '')), 
                        str(row.get('Part_of_Speech', '')), gender, str(row.get('Morphology', '')), 
                        str(row.get('Nuance','')),
                        sentences[0], sentences[1], sentences[2],
                        clean_trans,
                        str(row.get('Etymology', '')), 
                        str(row.get('Mnemonic','')), 
                        clean_analogues, 
                        f'<img src="{f_img}">' if has_img else "", 
                        str(row.get('Tags', '')),
                        f"[sound:{f_word}]" if has_w else "",
                        f_s1 if has_s1 else "", 
                        f_s2 if has_s2 else "", 
                        f_s3 if has_s3 else "",
                        f_word if has_w else "",
                        cloze_context,
                        uuid
                    ],
                    tags=str(row.get('Tags', '')).split(), guid=uuid
                )
                self.deck.add_note(note)

            except Exception as e:
                print(f"⚠️ Error processing row {index}: {e}")

    def export_package(self):
        """Експортувати колоду з резервною копією та статистикою"""
        filename = f"system_zero_{CURRENT_LANG.lower()}.apkg"
        valid_media = list(set([f for f in self.media_files if os.path.exists(f)]))
        
        # Обчислити розмір файлів
        total_size = sum(os.path.getsize(f) for f in valid_media if os.path.exists(f))
        self.stats['total_bytes'] = total_size
        
        # Резервна копія старого файлу
        if os.path.exists(filename):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"system_zero_{CURRENT_LANG.lower()}_{timestamp}.apkg"
            shutil.copy2(filename, backup_filename)
            print(f"💾 Резервна копія: {backup_filename}")
        
        # Створити пакет
        package = genanki.Package(self.deck)
        package.media_files = valid_media
        package.write_to_file(filename)
        
        # Показати детальну статистику
        self._print_statistics(filename, total_size)
        
        # Прибрати старі резервні копії (залишити останні 3)
        self._cleanup_old_backups()

    def _print_statistics(self, filename: str, total_size: int):
        """Показати детальний звіт статистики"""
        elapsed_time = time.time() - self.stats['start_time']
        minutes, seconds = divmod(int(elapsed_time), 60)
        
        img_total = self.stats['images_success'] + self.stats['images_failed']
        audio_w_total = self.stats['audio_word_success'] + self.stats['audio_word_failed']
        audio_s_total = self.stats['audio_sent_success'] + self.stats['audio_sent_failed']
        
        img_pct = (self.stats['images_success'] / img_total * 100) if img_total > 0 else 0
        audio_w_pct = (self.stats['audio_word_success'] / audio_w_total * 100) if audio_w_total > 0 else 0
        audio_s_pct = (self.stats['audio_sent_success'] / audio_s_total * 100) if audio_s_total > 0 else 0
        
        size_mb = total_size / (1024 * 1024)
        file_size = os.path.getsize(filename) / (1024 * 1024)
        
        print("\n" + "="*60)
        print("✨ СТАТИСТИКА ЗБИРАННЯ КОЛОДИ")
        print("="*60)
        print(f"✅ Слова обрані:              {self.stats['words_processed']}")
        print(f"📸 Зображення завантажені:   {self.stats['images_success']}/{img_total} ({img_pct:.1f}%)")
        print(f"🎵 Аудіо слів завантажені:   {self.stats['audio_word_success']}/{audio_w_total} ({audio_w_pct:.1f}%)")
        print(f"🎧 Аудіо речень завант.:     {self.stats['audio_sent_success']}/{audio_s_total} ({audio_s_pct:.1f}%)")
        print(f"⏱️  Час виконання:            {minutes}м {seconds}с")
        print(f"📦 Розмір медіа:              {size_mb:.1f} МБ")
        print(f"💾 Розмір файлу:             {file_size:.1f} МБ")
        print(f"📝 Файл створено:            {filename}")
        
        # Адаптивна паралелізація статистика
        if self.adaptive_stats['concurrency_adjustments'] > 0:
            print(f"\n⚙️ АДАПТИВНА ПАРАЛЕЛІЗАЦІЯ:")
            print(f"🔄 Зміни паралелізації:      {self.adaptive_stats['concurrency_adjustments']}")
            print(f"🔵 Поточна паралелізація:    {self.current_concurrency}/{Config.CONCURRENCY * 2}")
        
        print("="*60)

    def _cleanup_old_backups(self, keep_count: int = 3):
        """Видалити старі резервні копії, залишити тільки останні N"""
        pattern = f"system_zero_{CURRENT_LANG.lower()}_*.apkg"
        backups = sorted(Path('.').glob(pattern), key=os.path.getmtime, reverse=True)
        
        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink()
            except:
                pass

async def main():
    if not os.path.exists(Config.CSV_FILE):
        print(f"❌ Error: {Config.CSV_FILE} not found!")
        return
    try:
        print(f"🎤 Voice Selected: {Config.VOICE}")
        print(f"🌍 Mode: {CURRENT_LANG}")
        df = pd.read_csv(Config.CSV_FILE, sep='|', encoding='utf-8-sig').fillna('')
        print("🎲 Shuffling words...")
        df = df.sample(frac=1).reset_index(drop=True)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ CSV Error: {e}"); return

    builder = AnkiDeckBuilder()
    await builder._download_confetti_lib()
    
    # Прогрес-бар з tqdm
    print(f"📚 Processing {len(df)} words...\n")
    
    with atqdm(total=len(df), desc="Building deck", unit="word") as pbar:
        tasks = [builder.process_row(i, row, len(df), pbar) for i, row in df.iterrows()]
        await asyncio.gather(*tasks)
    
    builder.export_package()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n🛑 Aborted by user.")