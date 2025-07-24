from pathlib import Path
import functools
import wave
import os
import html

import gradio as gr
from piper import PiperVoice, SynthesisConfig
from phonemizer import phonemize

# ─────────────────────────────────────────────────────────────────────────────
# 1. Voice list  ──  表示名 → { model_path, phonemizer_language }
# ─────────────────────────────────────────────────────────────────────────────
# 使いたい音声モデルと、それに対応する phonemizer の言語コード(en-gb / en-us) を
# セットで管理しておく。
# これにより「選択した声のアクセントに合わせた IPA だけ」を動的に生成できる。
# ----------------------------------------------------------------------------
MODELS = {
    # ── British English : RP / 南部寄り ──
    "Alan · male · RP · medium": {
        "path": "./models/en_GB-alan-medium.onnx",
        "language": "en-gb",
    },
    "Cori · female · RP · high": {
        "path": "./models/en_GB-cori-high.onnx",
        "language": "en-gb",
    },
    "Semaine · female · RP · medium": {
        "path": "./models/en_GB-semaine-medium.onnx",
        "language": "en-gb",
    },
    # ── British English : ロンドン／南部カジュアル ──
    "Southern · female · London/Estuary · low": {
        "path": "./models/en_GB-southern_english_female-low.onnx",
        "language": "en-gb",
    },
    # ── British English : 北部・スコットランド・アイルランド ──
    "Northern · male · North-England · medium": {
        "path": "./models/en_GB-northern_english_male-medium.onnx",
        "language": "en-gb",
    },
    "Alba · male · Scottish · medium": {
        "path": "./models/en_GB-alba-medium.onnx",
        "language": "en-gb",
    },
    "Jenny · female · Irish · medium": {
        "path": "./models/en_GB-jenny_dioco-medium.onnx",
        "language": "en-gb",
    },
    # ── British English : ニュートラル ──
    "Aru · male · Neutral UK · medium": {
        "path": "./models/en_GB-aru-medium.onnx",
        "language": "en-gb",
    },
    "VCTK · male · Neutral UK · medium": {
        "path": "./models/en_GB-vctk-medium.onnx",
        "language": "en-gb",
    },
    # ── US English ──
    "Lessac · female · US · medium": {
        "path": "./models/en_US-lessac-medium.onnx",
        "language": "en-us",
    },
    "Norman · male · US · medium": {
        "path": "./models/en_US-norman-medium.onnx",
        "language": "en-us",
    },
    "Sam · male · US · medium": {
        "path": "./models/en_US-sam-medium.onnx",
        "language": "en-us",
    },
    "Ryan  · male · US · high": {
        "path": "./models/en_US-ryan-high.onnx",
        "language": "en-us",
    },
}

LANGUAGE_YOUGLISH = {
    "en-gb": "english/uk",
    "en-us": "english/us",
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Piper モデルをキャッシュロード
# ─────────────────────────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=len(MODELS))
def get_voice(model_path: str) -> PiperVoice:
    """Return a cached PiperVoice instance"""
    return PiperVoice.load(Path(model_path).expanduser())

# ─────────────────────────────────────────────────────────────────────────────
# 3. IPA 変換ヘルパー
# ─────────────────────────────────────────────────────────────────────────────
def to_ipa(text: str, language: str) -> str:
    """Return broad IPA transcription for the given text & language."""
    ipa_raw = phonemize(
        text,
        language=language,
        backend="espeak",
        with_stress=True,
        strip=False,
    )
    # ɐ → ə など“広い表記”へ寄せ、音節境界の . を除く
    return ipa_raw.replace("ɐ", "ə").replace(".", "")


# ─────────────────────────────────────────────────────────────────────────────
# 4. 単語レベル対応表 (Word ↔ IPA)
# ─────────────────────────────────────────────────────────────────────────────
def word_ipa_table(text: str, language: str) -> str:
    """Return HTML table mapping each word to its IPA transcription."""
    words = text.split()
    words = [w.strip(".,!?;:") for w in words]  # 単語の前後の句読点を除去
    ipas = phonemize(
        words,
        language=language,
        backend="espeak",
        strip=True,
        with_stress=True,
        njobs=1,
    )
    rows = [
        "<tr>"
        f"<td>{html.escape(w)}</td>"
        f"<td>{html.escape(ipa)}</td>"
        f"<td><a target=\"_blank\" href=\"https://youglish.com/pronounce/{html.escape(w)}/{LANGUAGE_YOUGLISH[language]}\">YouGlish</a></td>"
        f"<td><a target=\"_blank\" href=\"https://www.google.com/search?q=define+{html.escape(w)}\">Google</a></td>"
        f"<td><a target=\"_blank\" href=\"https://ejje.weblio.jp/content/{html.escape(w)}\">Weblio</a></td>"
        "</tr>"
        for w, ipa in zip(words, ipas)
    ]
    return "<table>" + "".join(rows) + "</table>"


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS + IPA + Table (メインコールバック)
# ─────────────────────────────────────────────────────────────────────────────

def tts_with_ipa(
    text: str,
    model_label: str,
    volume: float,
    length_scale: float,
    noise_scale: float,
    noise_w_scale: float,
    normalize_audio: bool,
):
    # ① 選択モデルの情報取得
    model_info = MODELS[model_label]
    lang = model_info["language"]
    text = text.replace("\n", " ")

    # ② Piper で音声生成
    voice = get_voice(model_info["path"])
    syn_cfg = SynthesisConfig(
        volume=volume,
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
        normalize_audio=normalize_audio,
    )
    wav_path = "output.wav"
    if os.path.exists(wav_path):
        os.remove(wav_path)
    with wave.open(wav_path, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=syn_cfg)

    # ③ IPA と対応表
    ipa = to_ipa(text, lang)
    table_html = word_ipa_table(text, lang)

    return wav_path, ipa, table_html


# ─────────────────────────────────────────────────────────────────────────────
# 6. Gradio UI
# ─────────────────────────────────────────────────────────────────────────────

demo = gr.Interface(
    fn=tts_with_ipa,
    inputs=[
        gr.Textbox(lines=2, label="Input Text"),
        gr.Dropdown(
            choices=list(MODELS.keys()),
            value=list(MODELS.keys())[0],
            label="Voice (accent)",
        ),
        gr.Slider(0.0, 1.0, value=0.5, step=0.05, label="Volume (0–1)"),
        gr.Slider(0.5, 3.0, value=1.0, step=0.05, label="Length Scale (↑ = slower)"),
        gr.Slider(0.0, 2.0, value=1.0, step=0.05, label="Noise Scale (timbre)"),
        gr.Slider(0.0, 2.0, value=1.0, step=0.05, label="Noise w Scale (prosody)"),
        gr.Checkbox(True, label="Normalize Audio"),
    ],
    outputs=[
        gr.Audio(type="filepath", label="Generated Audio"),
        gr.Textbox(label="IPA Transcription"),
        gr.HTML(label="Word ↔ IPA"),
    ],
    title="Piper TTS + IPA Viewer",
    description=(
        "Select a voice, enter text, and play the generated speech. "
        "The IPA transcription (matching the selected accent) and a word‑level table "
        "are displayed below."
    ),
)

if __name__ == "__main__":
    demo.launch(share=True)
