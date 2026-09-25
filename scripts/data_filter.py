import os
import gzip
import json
import time
from fastwarc.warc import ArchiveIterator, WarcRecordType
import argparse

from cs336_data.pii import mask_emails,mask_phone_numbers,mask_ips
from cs336_data.toxicity import classify_nsfw,classify_toxic_speech
from cs336_data.quality import gopher_quality_filter,classifier_quality
from cs336_data.deduplication import exact_line_deduplication_for_pipeline,minhash_deduplication_for_pipeline
from cs336_data.modal_utils import MODAL_SECRETS, VOLUME_MOUNTS, app, build_image,data_volume


@app.function(image=build_image(), volumes=VOLUME_MOUNTS, timeout=60 * 30)
def process_single_wet_file(input_file,output_file):
    output_dir=os.path.dirname(output_file)
    os.makedirs(output_dir,exist_ok=True)
    cleaned_docs=[]
    filter_num={}
    masked_num={}
    with gzip.open(input_file,"rb") as stream:
        for record in ArchiveIterator(stream):
            if record.record_type!=WarcRecordType.conversion:
                continue
            doc_byte=record.reader.read()
            doc=doc_byte.decode("utf-8",errors="replace")

            # 清洗
            if not gopher_quality_filter(doc):
                filter_num["gopher"]=filter_num.get("gopher",0)+1
                continue
            nsfw_label,_=classify_nsfw(doc)
            if nsfw_label=="nsfw":
                filter_num["nsfw"]=filter_num.get("nsfw",0)+1
                continue
            toxic_label,_=classify_toxic_speech(doc)
            if toxic_label=="toxic":
                filter_num["toxic"]=filter_num.get("toxic",0)+1
                continue
            quality_label,_=classifier_quality(doc)
            if quality_label=="cc":
                filter_num["quality"]=filter_num.get("quality",0)+1
                continue

            # 文本掩码
            doc,email_masked=mask_emails(doc)
            doc,phone_number_masked=mask_phone_numbers(doc)
            doc,ip_masked=mask_ips(doc)

            masked_num["email"]=masked_num.get("email",0)+email_masked
            masked_num["phone_number"]=masked_num.get("phone_number",0)+phone_number_masked
            masked_num["ip"]=masked_num.get("ip",0)+ip_masked
            cleaned_docs.append(doc)

    # 输出
    with open(output_file,"w",encoding="utf-8") as f:
        for doc in cleaned_docs:
            f.write(json.dumps(doc)+"\n")
    data_volume.commit()
    return filter_num,masked_num,len(cleaned_docs)

@app.function(image=build_image(), volumes=VOLUME_MOUNTS, timeout=60 * 30)
def clean_pipeline(use_min_hash_deduplication:bool):
    cleaned_doc_num=0
    filter_num={}
    masked_num={}
    filter_p={}
    masked_p={}
    filter_start_time=time.time()
    input_dir="/shared-data/english-wet-data"
    tmp_output_dir="/root/data/tmp_english-cleaned-data"
    final_output_dir="/root/data/english-cleaned-data"
    os.makedirs(tmp_output_dir,exist_ok=True)
    files=os.listdir(input_dir)
    input_files=[os.path.join(input_dir,file) for file in files if file.find(".warc.wet.gz")!=-1]
    output_files=[os.path.join(tmp_output_dir,file).replace(".warc.wet.gz",".jsonl") for file in files if file.find(".warc.wet.gz")!=-1]
    line_deduplication_output_files=[os.path.join(tmp_output_dir,file).replace(".warc.wet.gz",".txt") for file in files if file.find(".warc.wet.gz")!=-1]
    final_output_files=[os.path.join(final_output_dir,file).replace(".warc.wet.gz",".txt") for file in files if file.find(".warc.wet.gz")!=-1]

    for worker_data in process_single_wet_file.map(input_files,output_files):
        cleaned_doc_num+=worker_data[2]
        for key,value in worker_data[0].items():
            filter_num[key]=filter_num.get(key,0)+value
        for key,value in worker_data[1].items():
            masked_num[key]=masked_num.get(key,0)+value
    data_volume.reload()
 
    filter_total_num=sum(filter_num.values())
    masked_total_num=sum(masked_num.values())
    if filter_total_num !=0:
        for key,value in filter_num.items():
            filter_p[key]=value/filter_total_num
    if masked_total_num !=0:
        for key,value in masked_num.items():
            masked_p[key]=value/masked_total_num

    print(f"filter comsume time: {time.time()-filter_start_time}")

    deduplication_start_time=time.time()

    if use_min_hash_deduplication:
        line_total_docs,line_rest_p=exact_line_deduplication_for_pipeline(output_files,line_deduplication_output_files)
        min_hash_total_docs,min_hash_rest_p=minhash_deduplication_for_pipeline(line_deduplication_output_files,num_hashes=100,num_bands=10,ngrams=5,jaccard_threshold=0.8,output_files=final_output_files)
    else:
        line_total_docs,line_rest_p=exact_line_deduplication_for_pipeline(output_files,final_output_files)
        min_hash_total_docs=None
        min_hash_rest_p=None
    data_volume.commit()
    deduplication_comsume_time=time.time()-deduplication_start_time
    print(f"comsum_time: {deduplication_comsume_time :.4f}")
    return filter_total_num,masked_total_num,filter_p,masked_p,cleaned_doc_num,min_hash_total_docs,min_hash_rest_p,line_total_docs,line_rest_p
    

@app.local_entrypoint()
def main(use_min_hash_deduplication:bool=False):
    filter_total_num,masked_total_num,filter_p,masked_p,cleaned_doc_num,min_hash_total_docs,min_hash_rest_p,line_total_line_nums,line_rest_p=clean_pipeline.remote(use_min_hash_deduplication)
    print(f"过滤总文档数: {filter_total_num}")
    print(f"总掩码数: {masked_total_num}")
    print(f"各指标过滤比重: {filter_p}")
    print(f"各掩码比重: {masked_p}")
    print(f"过滤后留存比: {cleaned_doc_num/(cleaned_doc_num+filter_total_num)}")
    print(f"line_deduplication 参与总行数: {line_total_line_nums}")
    print(f"line_deduplication 行留存比: {line_rest_p}")
    if min_hash_total_docs is not None:
        print(f"min_hash参与总文档: {min_hash_total_docs}")
        print(f"min_hash留存比: {min_hash_rest_p}")
   





        

    





            

        

