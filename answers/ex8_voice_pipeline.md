# Ex8 — Voice pipeline

## Your answer

The voice pipeline has two modes with shared trace-event contract:
text mode (run_text_mode, shipped complete) reads stdin and the
manager persona replies via Llama-3.3-70B; voice mode (run_voice_mode)
uses Speechmatics for STT and Rime.ai for TTS.

The critical design choice is graceful degradation. run_voice_mode
checks SPEECHMATICS_KEY and the speechmatics-python import before
doing anything else. If either is missing, it logs a warning and
falls through to run_text_mode. Similarly, if RIME_API_KEY is
missing but STT is available, the manager's reply is printed to
stdout but not spoken, allowing partially configured environments
to still exercise the STT part of the loop.

Both modes emit voice.utterance_in and voice.utterance_out trace
events with payload {text, turn, mode}. The mode field tells the
grader which transport was in use. Same trace shape = identical
downstream analysis.

Evidence of successful voice interaction from `sess_5dd21769c8aa`:
- User: "I like to make a booking ." (Turn 0, Mode: voice)
- Manager: "How many in your party?"
- User: "Six ."
- Manager: "Aye, we can do that. I'll pencil you in for what date at what time?..."
- Result: "Aye, you're booked." (Turn 3)

The ManagerPersona class holds a conversation history list and calls
an LLM for each turn. It's deterministic given identical history +
model seed, which makes the tests stable even though we talk to a
real model.

## Citations

- starter/voice_pipeline/voice_loop.py — run_voice_mode
- starter/voice_pipeline/manager_persona.py — LLM-backed persona
