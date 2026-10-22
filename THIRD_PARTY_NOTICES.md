# Voice engines

HeyClone can download and run these optional engines locally:

- Chatterbox Nano by Resemble AI: https://github.com/resemble-ai/chatterbox
  and https://huggingface.co/ResembleAI/chatterbox-nano. Code and model: MIT.
  The notice is bundled at `heyclone/voice/licenses/Chatterbox.txt`.
  The engine's built-in audio watermark is preserved.
- Coqui XTTS v2: https://huggingface.co/coqui/XTTS-v2.
  Model: Coqui Public Model License 1.0.0, non-commercial use.
  Full terms are bundled at `heyclone/voice/licenses/XTTS.txt` and displayed
  in the app before use. The runtime uses the maintained `coqui-tts` package.

Python runtimes and dependencies are installed separately on demand. Their
respective licenses remain in the installed packages.
