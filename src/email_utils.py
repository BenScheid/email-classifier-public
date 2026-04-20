import config as cfg
import utils

def print_structure(obj, indent=0):
    """
    Prints the structure of a JSON-like object,
    showing keys and nesting, but no actual values.
    """

    spacer = "  " * indent

    if isinstance(obj, dict):
        print(f"{spacer}{{")
        for key, value in obj.items():
            print(f"{spacer}  \"{key}\":", end=" ")
            print_structure(value, indent + 1)
        print(f"{spacer}}},")

    elif isinstance(obj, list):
        print(f"[")
        if obj:
            print_structure(obj[0], indent + 1)
        print(f"{spacer}],")

    else:
        print(f"{spacer}<value>,")

def extract_all_text(payload: dict) -> str:
    """
    Extracts and combines all text/plain and text/html parts
    from a Gmail API message payload into a single string.
    """

    texts = []

    def walk(part):
        mime = part.get("mimeType", "")

        # If this part has sub-parts, recurse
        if "parts" in part:
            for sub in part["parts"]:
                walk(sub)
            return

        # Only care about text parts
        if mime in ("text/plain", "text/html"):
            data = part.get("body", {}).get("data")
            if not data:
                return
            text = utils.decode_b64(data)

            if mime == "text/html":
                # very light cleanup, enough for embeddings
                text = utils.clean_html(text)
                text = text.replace("<br>", "\n").replace("<br/>", "\n")

            text = utils.clean_invisible_chars(text)
            texts.append(text)

    walk(payload)

    return "\n".join(t.strip() for t in texts if t.strip())


def extract_parts(full_email):
    extracted = {}
    # sender & header
    #print_structure(full_email)
    headers = full_email["payload"]["headers"]
    for header in headers:
        if header["name"].lower() == "subject" or header["name"].lower() == "from":
            value = header["value"]
            normalized = utils.clean(value)
            extracted[header["name"].lower()] = normalized

    # timestamp
    extracted["time_ms"] = full_email["internalDate"]
    #body
    payload = full_email["payload"]
    cleaned = utils.clean(extract_all_text(payload))
    snippet_length = cfg.get_main().get("optimizations", {}).get("email_snippet_length", -1)
    if isinstance(snippet_length, int) and snippet_length >= 0:
        extracted["body"] = cleaned[:snippet_length]
    else:
        extracted["body"] = cleaned

    return extracted

def get_foreign_ids_for_names(mailboxes:list):
    result = {}
    for mb in mailboxes:
        result[mb["name"]] = mb["id"]
    return result
