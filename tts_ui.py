from pathlib import Path
import functools
import wave
import gradio as gr
from piper import PiperVoice, SynthesisConfig
import os

# ── 1. 表示名 → モデルファイルパス ──
MODELS = {
    # ── British English : RP / 南部寄り ──
    "Alan · male · RP · medium":           "~/.local/share/piper-voices/en_GB-alan-medium.onnx",
    "Cori · female · RP · medium":         "~/.local/share/piper-voices/en_GB-cori-medium.onnx",
    "Cori · female · RP · high":           "~/.local/share/piper-voices/en_GB-cori-high.onnx",
    "Semaine · female · RP · medium":      "~/.local/share/piper-voices/en_GB-semaine-medium.onnx",
    # ── British English : ロンドン／南部カジュアル ──
    "Southern · female · London/Estuary · low": "~/.local/share/piper-voices/en_GB-southern_english_female-low.onnx",
    # ── British English : 北部・スコットランド・アイルランド ──
    "Northern · male · North-England · medium": "~/.local/share/piper-voices/en_GB-northern_english_male-medium.onnx",
    "Alba · male · Scottish · medium":          "~/.local/share/piper-voices/en_GB-alba-medium.onnx",
    "Jenny · female · Irish · medium":          "~/.local/share/piper-voices/en_GB-jenny_dioco-medium.onnx",
    # ── British English : ニュートラル ──
    "Aru · male · Neutral UK · medium":         "~/.local/share/piper-voices/en_GB-aru-medium.onnx",
    "VCTK · male · Neutral UK · medium":        "~/.local/share/piper-voices/en_GB-vctk-medium.onnx",
    # ── 参考 US English ──
    "Lessac · female · US · medium":            "~/.local/share/piper-voices/en_US-lessac-medium.onnx",
}

# ── 2. 音声モデルをキャッシュロード ──
@functools.lru_cache(maxsize=len(MODELS))
def get_voice(model_path: str) -> PiperVoice:
    return PiperVoice.load(Path(model_path).expanduser())

# ── 3. TTS ──
def tts(
    text: str,
    model_label: str,
    volume: float,
    length_scale: float,
    noise_scale: float,
    noise_w_scale: float,
    normalize_audio: bool
):
    text = text.replace("\n", " ")
    voice = get_voice(MODELS[model_label])

    syn_config = SynthesisConfig(
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
        voice.synthesize_wav(text, wf, syn_config=syn_config)

    return wav_path

# ── 4. Gradio UI ──
demo = gr.Interface(
    fn=tts,
    inputs=[
        gr.Textbox(lines=2, label="Input Text"),
        gr.Dropdown(
            choices=list(MODELS.keys()),
            value=list(MODELS.keys())[0],
            label="Voice (British English)"
        ),
        gr.Slider(0.0, 1.0, value=0.5, step=0.05, label="Volume (0–1)"),
        gr.Slider(0.5, 3.0, value=1.0, step=0.05, label="Length Scale (speed: ↑値=遅い)"),
        gr.Slider(0.0, 2.0, value=1.0, step=0.05, label="Noise Scale (timbre)"),
        gr.Slider(0.0, 2.0, value=1.0, step=0.05, label="Noise w Scale (prosody)"),
        gr.Checkbox(True, label="Normalize Audio"),
    ],
    outputs=gr.Audio(type="filepath", label="Generated Audio"),
    title="Piper TTS · British/US Voices",
    description="Choose a voice and fine-tune synthesis parameters in real time.",
)

if __name__ == "__main__":
    demo.launch(share=True)
