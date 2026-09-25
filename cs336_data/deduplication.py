import os
import regex
import json
import mmh3
import unicodedata
from itertools import combinations
def exact_line_deduplication(input_files: list[os.PathLike], output_directory: os.PathLike):
    text_occu={}
    for input_file in input_files:
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        texts=text.split("\n")
        texts=texts[:-1]
        for line in texts:
            text_occu[line]=text_occu.get(line,0)+1


    for input_file in input_files:
        new_texts=[]
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        texts=text.split("\n")
        texts=texts[:-1]
        for line in texts:
            if text_occu[line]!=1:
                continue
            new_texts.append(line)

        _,input_file_name=os.path.split(input_file)
        output_path=os.path.join(output_directory,input_file_name)
        with open(output_path,"w",encoding="utf-8") as f:
            if new_texts==[]:
                f.write("")
            else:f.write("\n".join(new_texts)+"\n")


def text_cleaning(text:str):
    text=text.lower()
    PAT=r"([\p{Cc}\p{P}\p{M}\p{S}])"
    nfd_text = unicodedata.normalize("NFD", text)
    pattern=regex.compile(PAT)
    clean_text=pattern.sub(" ",nfd_text)
    return clean_text

def n_gram_doc(ngrams:int,text:str):
    words=text.split()
    doc=[" ".join(words[i:i+ngrams]) for i in range(len(words)-ngrams+1)]
    return doc

def jaccard_similarity(set_a:set,set_b:set):
        a_and_b=set_a&set_b
        a_or_b=set_a|set_b
        if len(a_or_b)==0:
            return 0.0
        jaccard=len(a_and_b)/len(a_or_b)
        return jaccard

def union(parent:dict[str,str],input_a,input_b):
    root_a=find(parent,input_a)
    root_b=find(parent,input_b)
    parent[root_b]=root_a

def find(parent:dict[str,str],input):
    if parent[input]==input:
        return input
    root=find(parent,parent[input])
    parent[input]=root
    return root


def minhash_deduplication(
    input_files: list[os.PathLike],
    num_hashes: int,
    num_bands: int,
    ngrams: int,
    jaccard_threshold: float,
    output_directory: os.PathLike,
):
    os.makedirs(output_directory, exist_ok=True)
    r=num_hashes//num_bands
    k_vec={}
    doc_sets={}
    band_hashs={}
    for input_file in input_files:
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        clean_text=text_cleaning(text)
        doc=n_gram_doc(ngrams,clean_text)
        doc_set=set(doc)
        doc_sets[input_file]=doc_set
        k_vec[input_file]=[]
        for k in range(num_hashes):
            min_hash=float('inf')
            for elm in doc_set:
                min_hash=min(mmh3.hash(elm,seed=k,signed=False),min_hash)
            k_vec[input_file].append(min_hash)

        current_k_vec=k_vec[input_file]
        for band_index in range(num_bands):
            band_key=(band_index,tuple(current_k_vec[band_index*r:band_index*r+r]))
            band_hashs[band_key]=band_hashs.get(band_key,[])
            band_hashs[band_key].append(input_file)

    candidates=set()
    for _,value in band_hashs.items():
        if len(value)>=2:
            candidates.update(list(combinations(value,2)))

    clean_candidates=[]
    for candidate in candidates:
        input_a,input_b=candidate
        doc_a=doc_sets[input_a]
        doc_b=doc_sets[input_b]
        jaccard=jaccard_similarity(doc_a,doc_b)
        if jaccard>jaccard_threshold:
            clean_candidates.append(candidate)

    
    parent={}
    cluster={}
    for input_file in input_files:
        parent[input_file]=input_file
    for clean_candidate in clean_candidates:
        input_a,input_b,=clean_candidate
        union(parent,input_a,input_b)
    for input_file in input_files:
        root=find(parent,input_file)
        cluster[root]=cluster.get(root,[])
        cluster[root].append(input_file)

    output_doc=[]
    for _,value in cluster.items():
        output_doc.append(value[0])

    for doc in output_doc:
        with open(doc,"r",encoding="utf-8") as f:
            text=f.read()
        _,output_file_name=os.path.split(doc)
        output_path=os.path.join(output_directory,output_file_name)
        with open(output_path,"w",encoding="utf-8") as f:
            f.write(text)

           
def exact_line_deduplication_for_pipeline(input_files: list[os.PathLike],output_files: os.PathLike):
    output_directory=os.path.dirname(output_files[0])
    os.makedirs(output_directory,exist_ok=True)
    text_occu={}
    total_line_num=0
    rest_line_num=0
    for input_file in input_files:
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        text=text.strip()
        docs=text.split("\n")
        for doc in docs:
            if not doc.strip():
                continue
            doc=json.loads(doc)
            lines=doc.split("\n")
            for line in lines:
                line_hash=mmh3.hash(line,seed=42)
                text_occu[line_hash]=text_occu.get(line_hash,0)+1
        
    for index,input_file in enumerate(input_files):
        new_text=[]
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        text=text.strip()
        docs=text.split("\n")
        for doc in docs:
            new_doc=[]
            doc_line_num=0
            if not doc.strip():
                continue
            doc=json.loads(doc)
            lines=doc.split("\n")
            for line in lines:
                if line.strip()=="":
                    continue
                total_line_num+=1
                line_hash=mmh3.hash(line,seed=42)
                if text_occu[line_hash]!=1:
                    continue
                rest_line_num+=1
                new_doc.append(line)
            new_doc=" ".join(new_doc)
            if new_doc != "":
                new_text.append(new_doc)
        new_text="\n".join(new_text)
        with open(output_files[index],"wt",encoding="utf-8") as f:
            f.write(new_text)
    if total_line_num!=0:
        rest_p=rest_line_num/total_line_num
    else:
        rest_p=0
    return total_line_num,rest_p

def minhash_deduplication_for_pipeline(
    input_files: list[os.PathLike],
    num_hashes: int,
    num_bands: int,
    ngrams: int,
    jaccard_threshold: float,
    output_files: os.PathLike,
):
    output_dir=os.path.dirname(output_files[0])
    os.makedirs(output_dir,exist_ok=True)
    r=num_hashes//num_bands
    splited_docs_set={}
    bands={}
    parent={}
    sign_vec={}
    total_docs_num=0
    rest_docs_num=0
    for input_file in input_files:
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        docs=text.split("\n")
        total_docs_num+=len(docs)
        for index,doc in enumerate(docs):
            if doc.strip()=="":
                continue
            key=f'{input_file}_{index}'
            parent[key]=key
            current_vec=[]
            cleaned_doc=text_cleaning(doc)
            splited_docs=n_gram_doc(ngrams,cleaned_doc)
            splited_doc_set=set(splited_docs)
            splited_docs_set[key]=splited_doc_set
            for k in range(num_hashes):
                min_hash=float('inf')
                for splited_doc in splited_doc_set:
                    doc_hash=mmh3.hash(splited_doc,seed=k)
                    min_hash=min(min_hash,doc_hash)
                current_vec.append(min_hash)    
            sign_vec[key]=current_vec

            for band_index in range(num_bands):
                band_key=(band_index,tuple(current_vec[band_index*r:band_index*r+r]))
                current_band=bands.get(band_key,[])
                current_band.append(key)
                bands[band_key]=current_band

    candidates=set()
    for _,value in bands.items():
        if len(value)>=2:
            candidates.update(list(combinations(value,2)))

    clean_candidates=[]
    for candidate in candidates:
        input_a,input_b=candidate
        doc_a=splited_docs_set[input_a]
        doc_b=splited_docs_set[input_b]
        jaccard=jaccard_similarity(doc_a,doc_b)
        if jaccard>jaccard_threshold:
            clean_candidates.append(candidate)

    cluster={}
    for clean_candidate in clean_candidates:
        input_a,input_b,=clean_candidate
        union(parent,input_a,input_b)
    for input_file in input_files:
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        docs=text.split("\n")
        for index,doc in enumerate(docs):
            if doc.strip()=="":
                continue
            key=f'{input_file}_{index}'
            root=find(parent,key)
            cluster[root]=cluster.get(root,[])
            cluster[root].append(key)

    output_docs=[]

    for _,value in cluster.items():
        output_docs.append(value[0])

    output_docs_set=set(output_docs)
    for index_file,input_file in enumerate(input_files):
        deduplicated_docs=[]
        with open(input_file,"r",encoding="utf-8") as f:
            text=f.read()
        docs=text.split("\n")
        for index_doc,doc in enumerate(docs):
            if doc.strip()=="":
                continue
            key=f"{input_file}_{index_doc}"
            if key in output_docs_set:
                deduplicated_docs.append(doc)
        rest_docs_num+=len(deduplicated_docs)
        deduplicated_text="\n".join(deduplicated_docs)
        with open(output_files[index_file],"wt",encoding="utf-8") as f:
            f.write(deduplicated_text)

    if total_docs_num!=0:
        rest_p=rest_docs_num/total_docs_num

    return total_docs_num,rest_p
                

            
                
                


    


    
            



    



            
            
