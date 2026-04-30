import os.path, email_utils
import config as cfg

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://mail.google.com/"]
TOKEN_PATH = ".configs/token.json"
CREDENTIALS_PATH = ".configs/credentials.json"

credentials = None

def load_credentials():
    global credentials
    # google doc
    if os.path.exists(TOKEN_PATH):
        credentials = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH, SCOPES
            )
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, "w") as token:
            token.write(credentials.to_json())

def get_service():
    global credentials
    if not credentials:
        return
    return build("gmail", "v1", credentials=credentials)

def get_inbox_id():
    return "INBOX"

def create_mailboxes(names:list, parent:str = None):
    label_builder = get_service().users().labels()
    prefix=""
    # optional parent mailbox
    if parent is not None and parent != "":
        prefix=parent+"/"

    result = {}
    for name in names:
        newMB = label_builder.create(userId="me", body={
            "name": prefix+name
        }).execute()

        result[newMB["name"]] = newMB["id"]
    return result

def list_mailboxes():
    service = get_service()
    result = service.users().labels().list(userId="me").execute()
    return result["labels"]

def label_exists(labels: list, label_name: str) -> bool:
    return any(label_name == label["name"] for label in labels)

def create_mailbox_if_not_exists():  
    config = cfg.get_main()
    load_credentials()
    mbs = list_mailboxes()
    names = [mb["name"] for mb in mbs]
    parent_name = config.get("parentMailBox") or ""

    default_name = cfg.get_main().get("default_category_name")
    if default_name and not label_exists(mbs, default_name):
        create_mailboxes([default_name])
        mbs = list_mailboxes()
        names = [mb["name"] for mb in mbs]

    if parent_name and parent_name not in names:
        create_mailboxes([parent_name])
        mbs = list_mailboxes()
        names = [mb["name"] for mb in mbs]

    for cat in config["categories"]:
        name = cat["name"]
        full_name = f"{parent_name}/{name}" if parent_name else name
        if full_name in names:
            continue
        create_mailboxes([name], parent=parent_name if parent_name else None)
        mbs = list_mailboxes()
        names = [mb["name"] for mb in mbs]

def list_unread_from_inbox():
    service = get_service()
    result = service.users().messages().list(userId="me", q="is:unread in:inbox").execute()
    ids = []
    msgs = result.get("messages")
    if not msgs:
        return ids
    for msg in msgs:
        ids.append(msg.get("id"))
    return ids

def load_emails_by_ids(ids: list) -> dict:
    service = get_service()
    messages = {}
    #for msg_id in ids:
    for msg_id in ids:
        email = service.users().messages().get(userId="me", id=msg_id).execute()
        #email_utils.print_structure(email)
        messages[msg_id] = email
    return messages

def load_cleaned_emails(ids:list) -> dict:
    emails = load_emails_by_ids(ids)
    cleaned = {}
    for id, email in emails.items():
        cleaned[id] = email_utils.extract_parts(email)

    return cleaned

def move_to_mailbox(msg_id, new_mb, remove_label_ids=None):
    srv = get_service()
    labels_to_remove = {get_inbox_id()}
    if remove_label_ids:
        labels_to_remove.update(label_id for label_id in remove_label_ids if label_id and label_id != new_mb)

    srv.users().messages().modify(userId="me", id=msg_id, body={
        "removeLabelIds": list(labels_to_remove),
        "addLabelIds": [new_mb]
    }).execute()

def get_label_id(label_name: str):
    labels = list_mailboxes()
    for label in labels:
        if label["name"] == label_name:
            return label["id"]
    return None
