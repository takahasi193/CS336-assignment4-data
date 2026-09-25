from cs336_data.extract import extract_text_from_html_bytes
from cs336_data.langid import identify_language
from cs336_data.pii import mask_emails,mask_phone_numbers,mask_ips
from cs336_data.toxicity import classify_nsfw,classify_toxic_speech
from cs336_data.quality import gopher_quality_filter
from cs336_data.modal_utils import VOLUME_MOUNTS, app, build_image, data_volume
import gzip
from fastwarc.warc import ArchiveIterator, WarcRecordType
import random
import fasttext
import os


def prepare_data(load_path, label: str, num_sample: int = 6000) -> list[str]:
    counter=0
    texts=[]
    with gzip.open(load_path,"rb") as stream:
         for record in ArchiveIterator(stream):
              if record.record_type != WarcRecordType.response:
                    continue
              if counter<num_sample:
                    counter+=1
                    html_bytes=record.reader.read()
                    text=extract_text_from_html_bytes(html_bytes)
                    lang_label,_=identify_language(text)
                    if lang_label=="en":
                         clean_text=" ".join(text.split())
                         if gopher_quality_filter(clean_text):
                              texts.append(f"__label__{label} {clean_text}")      
              else:
                    break

    return texts

  
@app.function(image=build_image(), volumes=VOLUME_MOUNTS, timeout=60 * 30)
def train_quality_classfier():
   import nltk
   nltk.download("punkt_tab", quiet=True)
   positive_sample=[]
   sample=[]
   for i in range(5):
        positive_sample.extend(prepare_data(load_path=f"/root/data/batch_{i}.warc.gz",label="wiki"))
   negative_sample=prepare_data(load_path="/shared-data/CC/example.warc.gz",label="cc")
   sample.extend(positive_sample)
   sample.extend(negative_sample)
   random.shuffle(sample)
   temp_path="/tmp/train_data.txt"
   with open(temp_path,"w",encoding="utf-8") as f:
        f.write("\n".join(sample) + "\n")
   model=fasttext.train_supervised(input="/tmp/train_data.txt", epoch=10, lr=0.5, wordNgrams=2)
   save_path="/root/data/quality_classifier.bin"
   model.save_model(save_path)
   data_volume.commit()
        

@app.local_entrypoint()
def main():
    train_quality_classfier.remote()

