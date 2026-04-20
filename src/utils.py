import uuid, html, base64, re, unicodedata, hashlib, config as cfg

def gen_uuid():
    return str(uuid.uuid4())

def prepare_passage(desc):
    return "passage: " + desc

def prepare_query(email):
    combined = ""
    if email.get("from"):
        combined += "From:\n" + email["from"]
    if email.get("subject"):
        combined += "Subject:\n" + email["subject"]
    if email.get("body"):
        combined += "Body:\n" + email["body"]
    return "query: " + combined

def gen_id_from_desc(desc:str):
    n = clean_invisible_chars(desc)
    encoded = n.encode("utf-8")
    return hashlib.md5(encoded, usedforsecurity=False).hexdigest()


def decode_b64(msg):
    return base64.urlsafe_b64decode(msg).decode("utf-8")

def clean_html(msg):
    text = html.unescape(msg)
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())

def clean_invisible_chars(text: str):
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u034F\u200B-\u200D\uFEFF\u00AD]", "", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def replace_urls(text:str):
    sub = cfg.get_main()["optimizations"]["overwrite_hyper_links"]
    if not sub:
        return text
    return re.sub(r"https?://\S+", sub, text)

def normalize_aggressive(text: str):
    return unicodedata.normalize("NFKD", text)

def clean(text:str):
    text = clean_html(text)
    text = clean_invisible_chars(text)
    text = normalize_aggressive(text)
    text = replace_urls(text)
    return text
