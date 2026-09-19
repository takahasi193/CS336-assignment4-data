from resiliparse.extract.html2text import extract_plain_text
from resiliparse.parse.encoding import detect_encoding
from fastwarc.warc import ArchiveIterator, WarcRecordType

def extract_text_from_html_bytes(html_bytes:bytes)->str | None:
    try:
        html_strs=html_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        html_encoding_type=detect_encoding(html_bytes)
        html_strs=html_bytes.decode(html_encoding_type,errors="replace")
    
    text=extract_plain_text(html_strs)
    return text
