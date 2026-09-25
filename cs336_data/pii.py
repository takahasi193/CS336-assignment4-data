import regex


def mask_emails(text:str)->tuple[str,int]:
    PAT=r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    pattern=regex.compile(PAT)
    new_text,num_masked=pattern.subn("|||EMAIL_ADDRESS|||",text)
    return new_text,num_masked


def mask_phone_numbers(text:str)->tuple[str,int]:
     PAT=r'(?:\(\d{3}\)[- ]?|\d{3}[- ]?)\d{3}[- ]?\d{4}'
     pattern=regex.compile(PAT)
     new_text,num_masked=pattern.subn("|||PHONE_NUMBER|||",text)
     return new_text,num_masked

def mask_ips(text:str)->tuple[str,int]:
     PAT=r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
     pattern=regex.compile(PAT)
     new_text,num_masked=pattern.subn("|||IP_ADDRESS|||",text)
     return new_text,num_masked