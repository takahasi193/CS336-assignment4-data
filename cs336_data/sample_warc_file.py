import gzip
import random
from fastwarc.warc import ArchiveIterator, WarcRecordType
from cs336_data.extract import extract_text_from_html_bytes
from cs336_data.langid import identify_language
from cs336_data.pii import mask_emails,mask_phone_numbers,mask_ips

warc_path = "local-shared-data/CC/example.warc.gz"

nums=random.sample(range(500),20)
nums=set(nums)
max_index=max(nums)
counter=0
texts=[]

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
    text,email_masked_num=mask_emails(text)
    text,phone_numbers_masked_num=mask_phone_numbers(text)
    text,ips_masked_num=mask_ips(text)
    print((email_masked_num,phone_numbers_masked_num,ips_masked_num))
    print(text[:1000])

