# 🇩🇪 System Zero: Anki Deck Generator

> Automated pipeline for creating **high-fidelity, beautiful Anki flashcards** for language learning with AI-generated audio, images, and modern glassmorphism design.

**Version:** 61.1 | **Status:** ✅ Production Ready | **Languages:** German (DE), English (EN)

---

## ✨ Features

### 📚 **Smart Card Generation**

- **Neural TTS Audio** - High-quality German/English voice synthesis via Microsoft Edge-TTS
- **AI Images** - Automatic image fetching from Pollinations AI API
- **4 Card Types** - Recognition, Production, Listening, Context Cloze
- **Rich Metadata** - Etymology, morphology, mnemonics, analogues, contextual examples

### ⚡ **Performance & Reliability**

- **Adaptive Parallelization** - Automatically adjusts concurrency based on server response
- **Smart Caching** - JSON cache prevents re-downloading of existing files (2x speed on re-run)
- **Exponential Backoff** - Intelligent retry logic with jitter for network resilience
- **Progress Tracking** - Real-time progress bar with ETA

### 🎨 **Beautiful Design**

- **Glassmorphism UI** - Modern CSS with gradient backgrounds
- **Color-Coded Genders** - German articles (der=blue, die=red, das=green, no article=purple)
- **Responsive Layout** - Works on desktop, tablet, and mobile Anki apps
- **Professional Typography** - System fonts, proper spacing, readable contrast

### 💾 **Data Management**

- **Automatic Backups** - Timestamped `.apkg` backups with cleanup
- **Detailed Statistics** - Comprehensive build report with success rates
- **Multi-Language Support** - Easy switching between DE/EN languages

---

## 📋 Requirements

- **Python 3.10+**
- **Anki 2.1+** or AnkiDroid
- **Internet connection** (for TTS and image generation)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/anki-system-zero.git
cd anki-system-zero
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 📖 Quick Start

### 1. Prepare Your Vocabulary CSV

Create `vocabulary.csv` with pipe-separated values:

```csv
TargetWord|Meaning|IPA|Part_of_Speech|Gender|Morphology|Nuance|ContextSentences|ContextTranslation|Etymology|Mnemonic|Analogues|Image|Tags
der Baum|tree|/baʊm/|Noun|der|Pl: -e|Common plant with leaves...|1. Der <b>Baum</b> ist groß.<br>2. Viele Bäume im Wald.|1. The tree is big.<br>2. Many trees in the forest.|From Proto-Germanic...|Remember: BOOM sound when tree falls|EN: tree<br>RU: дерево<br>UA: дерево|https://image.pollinations.ai/prompt/tree%20icon?width=320&height=200|Noun A1 Nature
```

**Column Reference:**

| Column             | Required | Description                                |
| ------------------ | -------- | ------------------------------------------ |
| TargetWord         | ✅       | Word/phrase to learn                       |
| Meaning            | ✅       | Definition                                 |
| IPA                | ✅       | Pronunciation                              |
| Part_of_Speech     | ✅       | Noun, Verb, Adjective, etc                 |
| Gender             | ✅       | (DE) der/die/das, (EN) en                  |
| Morphology         | ❌       | Grammar notes                              |
| Nuance             | ❌       | Usage context                              |
| ContextSentences   | ✅       | Example sentences (3, separated by `<br>`) |
| ContextTranslation | ✅       | Translation of examples                    |
| Etymology          | ❌       | Word origin                                |
| Mnemonic           | ✅       | Memory hook                                |
| Analogues          | ❌       | Similar words (EN: word / DE: wort)        |
| Image              | ❌       | Image URL or prompt                        |
| Tags               | ❌       | Space-separated tags                       |

### 2. Run the Build Script

```bash
python build_deck.py
```

**Output Example:**

```
🎤 Voice Selected: de-DE-ConradNeural
🌍 Mode: DE
🎲 Shuffling words...
📚 Processing 54 words...

Building deck: 100%|██████████████████| 54/54 [01:56<00:00, 2.15s/word]

💾 Резервна копія: system_zero_de_20251225_151159.apkg

============================================================
✨ СТАТИСТИКА ЗБИРАННЯ КОЛОДИ
============================================================
✅ Слова обрані:              54
📸 Зображення завантажені:   54/54 (100.0%)
🎵 Аудіо слів завантажені:   54/54 (100.0%)
🎧 Аудіо речень завант.:     162/162 (100.0%)
⏱️  Час виконання:            1м 59с
📦 Розмір медіа:              2.6 МБ
💾 Розмір файлу:             2.8 МБ
📝 Файл створено:            system_zero_de.apkg
============================================================
```

### 3. Import into Anki

**Desktop Anki:**

1. Open Anki → File → Import...
2. Select `system_zero_de.apkg`
3. Click "Import" button

**AnkiDroid (Mobile):**

1. Open AnkiDroid → Menu → Import
2. Select the `.apkg` file
3. Tap "Import"

---

## ⚙️ Configuration

Edit the `Config` dataclass in `build_deck.py`:

```python
# Language selection
CURRENT_LANG = "DE"  # or "EN"

# Performance tuning
CONCURRENCY = 4                    # Parallel downloads (1-8 recommended)
RETRIES = 5                        # Retry attempts (3-7)
TIMEOUT = 60                       # General timeout in seconds
IMAGE_TIMEOUT = 90                 # Image generation timeout
REQUEST_DELAY_MIN = 0.5            # Min delay between requests
REQUEST_DELAY_MAX = 3.5            # Max delay between requests
```

---

## 📊 Performance

Benchmark on 54-word vocabulary (modern system):

| Scenario          | Time    | Speed            | Notes                         |
| ----------------- | ------- | ---------------- | ----------------------------- |
| First build       | ~23 min | N/A              | Generates all audio & images  |
| Cached build      | ~2 min  | **11.5x faster** | Uses cached files             |
| Per-word (cached) | 2.15s   | -                | With adaptive parallelization |
| Success rate      | 100%    | -                | Images + audio                |

---

## 🔧 Advanced Features

### Adaptive Parallelization

System automatically optimizes concurrency:

- Detects HTTP 429 (too many requests) → reduces parallelization by 50%
- Detects 5+ successful requests → doubles parallelization
- Adapts to server capacity in real-time
- Progress bar shows current concurrency level

### Smart Caching

- Downloads cached in `build_cache.json`
- Prevents redundant API calls
- ~2x faster on re-runs
- Automatic cache validation

### Automatic Backups

- Timestamped backups: `system_zero_de_20251225_151159.apkg`
- Keeps last 3 versions automatically
- No data loss on script re-run
- Easy rollback to previous versions

---

## 📁 Directory Structure

```
anki-system-zero/
├── build_deck.py              # Main build script (800+ lines)
├── test_improvements.py       # Test suite
├── vocabulary.csv             # Your vocabulary data
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── .gitignore                # Git ignore rules
│
├── build_cache.json          # (Generated) Download cache
├── system_zero_de.apkg       # (Generated) Anki deck
│
└── media/                    # (Generated) Downloaded assets
    ├── _word_*.mp3          # TTS audio files
    ├── _img_*.jpg           # Fetched images
    ├── _sent_*.mp3          # Sentence audio
    └── _confetti.js         # Animation library
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'tqdm'"

```bash
pip install tqdm
```

### "HTTP 502 Bad Gateway" errors

- Normal - server is overloaded
- System uses exponential backoff + jitter
- Will retry automatically
- Reduces parallelization if persistent

### "Timeout during image generation"

- Pollinations AI might be slow
- Increase `IMAGE_TIMEOUT` in config
- Try running at different time of day

### Images not downloading

- Check image URL in CSV
- Ensure image URLs are complete
- Verify internet connection
- Check `media/` folder permissions

---

## 🤝 Contributing

### Found a bug?

1. Check [existing issues](../../issues)
2. Create detailed report with:
   - Reproduction steps
   - CSV sample (sanitized)
   - Full error message
   - Python version

### Have suggestions?

- Open [discussion](../../discussions)
- Or create [feature request](../../issues)

### Want to contribute code?

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open Pull Request

**Current needs:**

- [ ] French (FR) language support
- [ ] Web UI dashboard
- [ ] Database backend
- [ ] Mobile app
- [ ] More language packs

---

## 🔐 Privacy & Safety

- ✅ **No data collection** - Fully local processing
- ✅ **No tracking** - No analytics or telemetry
- ✅ **Open source** - Complete source code available
- ⚠️ **External APIs used:**
  - Microsoft Edge-TTS (for audio synthesis)
  - Pollinations AI (for image generation)
  - All data sent encrypted over HTTPS

**Recommendation:** Review API terms of service before deploying at scale.

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for full text

```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files...
```

---

## 🙏 Credits & Acknowledgments

- **Genanki** - For Anki deck generation
- **Edge-TTS** - For neural text-to-speech
- **Pollinations AI** - For image generation
- **Anki Community** - For the learning platform
- **All contributors** - For feedback and improvements

---

## 📈 Roadmap

### v61.2 (Q1 2026)

- [ ] Multi-language UI (German, Ukrainian, Russian)
- [ ] Web dashboard
- [ ] Custom CSS themes
- [ ] French language pack

### v62.0 (Q2 2026)

- [ ] PostgreSQL database backend
- [ ] Cloud sync support
- [ ] Mobile companion app
- [ ] Spaced repetition analytics

---

## 💬 Support & Community

- **Issues & Bugs:** [GitHub Issues](../../issues)
- **Questions:** [GitHub Discussions](../../discussions)
- **Anki Forum:** [ankiweb.net](https://ankiweb.net)

---

**Built with ❤️ for language learners worldwide**

_Last updated: December 25, 2025_
