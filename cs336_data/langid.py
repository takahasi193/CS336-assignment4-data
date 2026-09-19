from typing import Any
from cs336_data.common import get_shared_assets_path
import fasttext

model_path = get_shared_assets_path() / "classifiers" / "lid.176.bin"

_LID_MODEL = None
def get_lid_model():
    global _LID_MODEL
    if _LID_MODEL is None:
        _LID_MODEL = fasttext.load_model(str(model_path))
    return _LID_MODEL

def identify_language(text:str)->tuple[Any,float]:
    lid_model=get_lid_model()
    clean_text = text.replace("\n", " ").strip()
    labels,scores=lid_model.predict(clean_text,k=1)
    lang=labels[0].replace("__label__","")
    score=float(scores[0])

    return lang,score
