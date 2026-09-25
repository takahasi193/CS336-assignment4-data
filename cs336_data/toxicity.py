from typing import Any
import fasttext
from cs336_data.common import get_shared_assets_path
_NSFW_MODEL = None
_TOXIC_MODEL=None
nsfw_model_path = get_shared_assets_path() / "classifiers" / "dolma_fasttext_nsfw_jigsaw_model.bin"
toxic_model_path = get_shared_assets_path() / "classifiers" / "dolma_fasttext_hatespeech_jigsaw_model.bin"

def get_nsfw_model():
    global _NSFW_MODEL
    if _NSFW_MODEL is None:
        _NSFW_MODEL = fasttext.load_model(str(nsfw_model_path))
    return _NSFW_MODEL

def get_toxic_model():
    global _TOXIC_MODEL
    if _TOXIC_MODEL is None:
        _TOXIC_MODEL = fasttext.load_model(str(toxic_model_path))
    return _TOXIC_MODEL

def classify_nsfw(text)->tuple[Any,float]:
    nsfw_model=get_nsfw_model()
    clean_text=text.replace("\n","").strip()
    labels,scores=nsfw_model.predict(clean_text,k=1)
    label=labels[0].replace("__label__","")
    score=float(scores[0])
    return label,score

def classify_toxic_speech(text)->tuple[Any,float]:
    toxic_model=get_toxic_model()
    clean_text=text.replace("\n","").strip()
    labels,scores=toxic_model.predict(clean_text,k=1)
    label=labels[0].replace("__label__","")
    score=float(scores[0])
    return label,score