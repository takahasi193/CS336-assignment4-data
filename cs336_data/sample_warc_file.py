import gzip
import random
from fastwarc.warc import ArchiveIterator, WarcRecordType
from cs336_data.extract import extract_text_from_html_bytes
from cs336_data.langid import identify_language
from cs336_data.pii import mask_emails,mask_phone_numbers,mask_ips
from cs336_data.toxicity import classify_nsfw,classify_toxic_speech

warc_path = "local-shared-data/CC/example.warc.gz"

nums=random.sample(range(500),300)
nums=set(nums)
max_index=max(nums)
counter=0
texts=[]
en_texts=[]

with gzip.open(warc_path, "rb") as stream:
    for record in ArchiveIterator(stream):
        if record.record_type != WarcRecordType.response:
            continue

        if counter in nums:
            html_bytes=record.reader.read()
            text=extract_text_from_html_bytes(html_bytes)
            texts.append(text)

        if counter == max_index:
            break
        counter+=1

for text in texts:
    label,score=identify_language(text)
    if label=='en' and score>=0.9:
        en_texts.append(text)

for text in en_texts:
    print(classify_nsfw(text))
    print(classify_toxic_speech(text))
    print(text[:500])

