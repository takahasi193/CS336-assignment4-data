from typing import Any
import nltk
import fasttext

nltk.download("punkt_tab", quiet=True)
model_path="data/quality_classifier.bin"
_QUALITY_MODEL=None

def get_quality_model():
    global _QUALITY_MODEL
    if _QUALITY_MODEL is None:
        _QUALITY_MODEL=fasttext.load_model(str(model_path))

    return _QUALITY_MODEL



def gopher_quality_filter(text:str)->bool:
    text_lines=text.split('\n')
    text_len=0
    symbol_word_len=0
    end_punc=0
    word_num=0
    alpha_word_num=0
    for line in text_lines:
        line=line.strip()
        if line.endswith("..."):
            end_punc+=1
        line_words=line.split(" ")
        line_words_len=len(line_words)
        for word in line_words:
            if not any(c.isalnum() for c in word):
                symbol_word_len+=1
                line_words_len-=1
                continue

            if any(c.isalpha() for c in word):
                alpha_word_num+=1

            text_len+=len(word)

        word_num+=line_words_len

    if word_num < 50 or word_num > 100000:
        return False

    avg_len=text_len/word_num

    if avg_len < 3 or avg_len > 10:
        return False

    if end_punc/len(text_lines) > 0.3:
        return False

    if alpha_word_num/word_num < 0.8:
        return False

    return True

def classifier_quality(text):
    classifier_model=get_quality_model()
    clean_text = text.replace("\n", " ").strip()
    labels,scores=classifier_model.predict(clean_text,k=1)
    label=labels[0].replace("__label__","")
    label=label.lower()
    score=float(scores[0])
    return label,score
            






    
  