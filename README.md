# Mail Dictation Assistant

A single self-contained HTML page for drafting email replies by voice, with an
optional AI "reply assistant" that turns rough dictated notes into a polished,
consultant-style reply.

## What it does

1. **Upload or paste a mail** — drop a `.msg`, `.eml`, or `.txt` file (or paste
   the text) into the left panel.
   - `.eml` files are parsed as MIME: multipart, base64/quoted-printable
     encodings, arbitrary charsets, and RFC 2047-encoded headers are all
     decoded, so From/To/Subject/body show up correctly instead of garbled text.
   - `.msg` files (Outlook's binary format) are parsed with a small parser
     library loaded on demand from a CDN — this needs an internet connection
     the first time you use it (see **Requirements** below).
   - The reply's "To"/"Subject" fields are pre-filled from the parsed headers.
2. **Skip the upload entirely** — use the mode switch at the top
   ("✍️ Write a new mail") to hide the upload panel and compose from scratch.
3. **Dictate rough notes** — choose **English** or **German**, press
   **Start Dictation**, and just talk — bullet fragments and half-sentences
   are fine, they land in the "Your notes" box live as you speak.
4. **Draft with AI** — press **✨ Draft reply with AI** to turn the original
   mail + your notes into a short, professional reply (see **Style** below).
   The draft appears in the "Polished reply" box, fully editable. Prefer to
   skip AI? **➡️ Use notes as reply** just copies your notes straight across.
5. **Export the reply** — copy it to the clipboard, or download it as a
   `.txt` or ready-to-send `.eml` file.

There's also a **"Read mail aloud"** button that reads the original mail back
to you (text-to-speech) in the currently selected language.

## AI reply style

The AI assistant is instructed to write like an experienced consultant/manager:
short, precise, calm and confident, no filler or corporate jargon, bullets for
multiple points/next steps, and — if the incoming mail is ambiguous — it flags
what needs clarification instead of guessing.

## Requirements

Just open `index.html` in **Google Chrome** or **Microsoft Edge** (the
[Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
used for dictation isn't supported in Firefox or Safari). You can open the
file directly (double-click it) or serve it locally, e.g.:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/
```

- **Dictation**: Chromium browser, microphone permission, internet connection
  (speech recognition runs in the browser's cloud speech service).
- **.msg upload**: internet connection (loads the parser library from a CDN
  the first time; `.eml`/`.txt` work fully offline).
- **AI drafting**: your own [Anthropic API key](https://console.anthropic.com/settings/keys),
  pasted into the "AI Reply Assistant" box. It's stored only in your browser's
  `localStorage` and sent directly from your browser to Anthropic's API —
  never anywhere else. Everything else in the app works without a key.

No build step, no server-side code, no bundler — everything runs in a single
HTML file.
