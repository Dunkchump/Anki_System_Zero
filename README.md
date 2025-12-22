# 🇩🇪 System Zero: Anki Deck Generator

Automated pipeline for creating high-fidelity, aesthetic Anki flashcards for language learning.
Built with Python, Genanki, and Edge-TTS.

## Features

- **Automatic Audio:** Generates high-quality neural TTS for words and context sentences.
- **Visuals:** Automatically fetches images via Pollinations AI.
- **Glassmorphism Design:** Modern, iOS-style CSS layout for Anki cards.
- **Academic Depth:** Supports deep morphology, etymology, and mnemonics.
- **Resilient:** Handles network timeouts and rate limits automatically.

## Requirements

- Python 3.x
- AnkiDroid / Anki Desktop

## Installation

```bash
pip install genanki pandas edge-tts requests
```

````

## Usage

1. Add words to `vocabulary.csv` (Pipe-separated).
2. Run the build script:

```bash
python build_deck.py

```

3. Import the generated `.apkg` file into Anki.

## CSV Structure

`TargetWord|Meaning|IPA|Part_of_Speech|Gender|Morphology|Nuance|ContextSentences|ContextTranslation|Etymology|Mnemonic|Analogues|Image|Tags`
````
