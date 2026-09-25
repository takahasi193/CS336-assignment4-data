import multiprocessing
import numpy as np
from tqdm import tqdm
import os
import time
from cs336_data.modal_utils import MODAL_SECRETS, VOLUME_MOUNTS, app, build_image,data_volume

from transformers import AutoTokenizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

tokenizer = None

def initial_tokenizer():
  global tokenizer
  if tokenizer is None:
     tokenizer=AutoTokenizer.from_pretrained("gpt2")

def tokenize_line_and_add_eos(line):
 return tokenizer.encode(line) + [tokenizer.eos_token_id]

@app.function(cpu=8,image=build_image(), volumes=VOLUME_MOUNTS, timeout=60 * 60 * 2)
def tokenize_data():
 input_dir="/root/data/english-cleaned-data"
 output_path="/root/data/train.bin"
 output_dir=os.path.dirname(output_path)
 os.makedirs(output_dir,exist_ok=True)
 files=os.listdir(input_dir)
 files=sorted(files)
 input_paths=[os.path.join(input_dir,file) for file in files if file.endswith(".txt")]
 start_time=time.perf_counter()
 total_token_num=0
 with open(output_path,"wb") as f_write:
    pool = multiprocessing.Pool(multiprocessing.cpu_count(),initializer=initial_tokenizer,)
    for input_path in input_paths:
        with open(input_path) as f_read:
            lines = f_read.readlines()
        cleaned_lines=[line for line in lines if line.strip()!=""]
        chunksize = 100
        results = []
        for result in tqdm(
        pool.imap(tokenize_line_and_add_eos, cleaned_lines, chunksize=chunksize),
        total=len(cleaned_lines),
        desc="Tokenizing lines"
        ):  
            results.append(result)
        # Flatten the list of ids and convert to numpy array
        all_ids = [token_id for sublist in results for token_id in sublist]
        total_token_num+=len(all_ids)
        print(f"Tokenized and encoded {input_path} into {len(all_ids)} tokens")
        ids_array = np.array(all_ids, dtype=np.uint16)
        ids_array.tofile(f_write)
    pool.close()
    pool.join()
 end_time=time.perf_counter()
 elapsed=end_time-start_time
 print(f"tokenize data process elapsed: {elapsed :.4f}")
 assert os.path.getsize(output_path) == total_token_num * 2
 data_volume.commit()
 return total_token_num

@app.local_entrypoint()
def main():
   total_token_num=tokenize_data.remote()
   print(f"total processed tokens: {total_token_num}")


       
