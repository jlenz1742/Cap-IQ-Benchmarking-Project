# Mail Dictation Assistant

A single self-contained HTML page for drafting email replies by voice.

## What it does

1. **Upload or paste a mail** — drop a `.eml`/`.txt` file (or paste the text) into
   the left panel. If it's a `.eml` file, the From/To/Subject/Date headers are
   parsed and shown, and the reply's "To"/"Subject" fields are pre-filled.
2. **Dictate your reply** — choose **English** or **German** with the language
   toggle, press **Start Dictation**, and speak. Your speech is transcribed
   live into the reply box (you can switch languages mid-reply — dictation
   restarts automatically with the new language).
3. **Export the reply** — copy it to the clipboard, or download it as a
   `.txt` or ready-to-send `.eml` file.

There's also a **"Read mail aloud"** button that uses text-to-speech to read
the original mail back to you in the currently selected language.

## Usage

Just open `index.html` in **Google Chrome** or **Microsoft Edge** (the
[Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
used for dictation is not supported in Firefox or Safari). You can open the
file directly (double-click it) or serve it locally, e.g.:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

**Requirements for dictation to work:**
- A Chromium-based browser (Chrome/Edge).
- Microphone permission granted to the page when prompted.
- An active internet connection (speech recognition is processed by the
  browser's cloud speech service).

No build step, no dependencies, no server-side code — everything runs in a
single HTML file.
