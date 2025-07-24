intall library
```sh
python -m venv piper-venv
source piper-venv/bin/activate
pip install -r requirements.txt
```


download models
```sh
mkdir models
cd models
python -m piper.download_voices en_GB-alan-medium
python -m piper.download_voices en_GB-cori-medium
python -m piper.download_voices en_GB-cori-high
python -m piper.download_voices en_GB-semaine-medium
python -m piper.download_voices en_GB-southern_english
python -m piper.download_voices en_GB-northern_english_male
python -m piper.download_voices en_GB-alba-medium
python -m piper.download_voices en_GB-jenny_dioco-medium
python -m piper.download_voices en_GB-aru-medium
python -m piper.download_voices en_GB-vctk-medium
python -m piper.download_voices en_US-lessac-medium
```

start server
```sh
python tts_ui.py
```
