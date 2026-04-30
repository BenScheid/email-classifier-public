import gmail_client as client
import utils
import config as cfg
import email_utils
import nli_model as nli
import embedding_model as emb
import json
import numpy as np
import sys
import os
from gmail_client import TOKEN_PATH

MIN_SCORE = 0.55

def resolve_foreign_id(name: str, parent_name: str, foreign_ids: dict):
    direct = foreign_ids.get(name)
    if direct:
        return direct
    if parent_name:
        return foreign_ids.get(f"{parent_name}/{name}")
    return None

def update_categories():
    config = cfg.get_main()
    categories:list = cfg.get_categories() or []

    mailboxes = client.list_mailboxes()
    foreign_ids:dict = email_utils.get_foreign_ids_for_names(mailboxes)
    parent_name = (config.get("parentMailBox") or "").strip()
    cached_cats = {}
    for c in categories:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        # Prefer entries that already carry a valid foreign_id.
        if key not in cached_cats or (not cached_cats[key].get("foreign_id") and c.get("foreign_id")):
            cached_cats[key] = c

    merged = []

    for newCat in config.get("categories", []):
        name = (newCat.get("name") or "").strip()
        desc = (newCat.get("description") or "").strip()

        if not name or not desc:
            continue

        key = name.lower()
        current = cached_cats.get(key, {})
        merged.append({
            "id": current.get("id") or utils.gen_id_from_desc(desc),
            "foreign_id": resolve_foreign_id(name, parent_name, foreign_ids) or current.get("foreign_id"),
            "name": name,
            "description": desc
        })

    cfg.saveToFile(cfg.CATEGORIES_KEY, merged)
    cfg.load_categories()

    
# returns dict[id -> vec]
def get_category_vectors():
    categories = cfg.get_categories()
    vectors = {}
    for cat in categories:
        foreign_id = cat.get("foreign_id")
        if not foreign_id:
            continue

        print("embedding cat: " + cat["name"])
        vec = embed_category(prepare_category_embed(cat))

        vectors[foreign_id] = vec

    return vectors

def prepare_category_embed(cat):
    return cat["name"]+". "+cat["description"]

# returns id of best match / -1 for no confident match
def compare_against_categories(email_vec, cat_vecs, default_label_id):
    categories = cfg.get_categories()
    bestMatch = {
        "id": default_label_id,
        "score": MIN_SCORE
    }

    #for id, vec in categories.items():
    for cat in categories:
        id = cat["foreign_id"]
        cos_score = emb.cos(email_vec, cat_vecs[id])
        print(id + ": " + str(cos_score))
        if cos_score > bestMatch["score"]:
            bestMatch["id"] = id
            print("best match: print"+id)

    #print(bestMatch)
    return bestMatch

def embed_category(desc):
    return emb.embed(utils.prepare_passage(desc))

def get_managed_label_ids():
    label_ids = set()
    default_name = cfg.get_main().get("default_category_name")
    if default_name:
        default_id = client.get_label_id(default_name)
        if default_id:
            label_ids.add(default_id)

    for cat in cfg.get_categories() or []:
        foreign_id = cat.get("foreign_id")
        if foreign_id:
            label_ids.add(foreign_id)

    return label_ids

def run_embeddings():
    categories = get_category_vectors()
    default_label_id = client.get_label_id(cfg.get_main().get("default_category_name"))
    if not default_label_id:
        raise RuntimeError("Default category label does not exist.")
    managed_label_ids = get_managed_label_ids()

    ids = client.list_unread_from_inbox()
    emails = client.load_cleaned_emails(ids)

    for id, email in emails.items():
        vec = emb.embed(utils.prepare_query(email))
        print("\n\n-------------------")
        print(email["subject"])
        category = compare_against_categories(vec, categories, default_label_id)
        client.move_to_mailbox(id, category["id"], remove_label_ids=managed_label_ids)


def run_nli():
    default_label_name = cfg.get_main().get("default_category_name")
    default_label_id = client.get_label_id(default_label_name)
    if not default_label_id:
        raise RuntimeError("Default category label does not exist.")

    managed_label_ids = get_managed_label_ids()
    configured_categories = cfg.get_categories() or []

    ids = client.list_unread_from_inbox()
    emails = client.load_cleaned_emails(ids)
    print(json.dumps(emails, indent=4))

    nli.load_model()

    for id, email in emails.items():
        sequence = nli.format_email_for_nli(email)

        print("\n\n-------------------")
        print(email.get("subject", "<no subject>"))

        prediction = nli.predict_best_category(sequence, configured_categories)
        if prediction is None or prediction.score < MIN_SCORE:
            chosen_label_id = default_label_id
            print(f"default match: {default_label_name} ({prediction.score if prediction else 'no-score'})")
        else:
            chosen_label_id = None
            for cat in configured_categories:
                if cat.get("name") == prediction.category_name:
                    chosen_label_id = cat.get("foreign_id")
                    break

            if not chosen_label_id:
                chosen_label_id = default_label_id
                print(f"missing mailbox id for category: {prediction.category_name}, using default")
            else:
                print(f"best match: {prediction.category_name} ({prediction.score})")

        client.move_to_mailbox(id, chosen_label_id, remove_label_ids=managed_label_ids)


cfg.load_main()
cfg.load_categories()

client.load_credentials()
client.create_mailbox_if_not_exists()
update_categories()

preferences = cfg.get_main()["preferences"]
if preferences["model_type"] == "embedding":
    run_embeddings()
elif preferences["model_type"] == "nli":
    run_nli()
else:
    sys.exit(1)

store_token = preferences["store_gmail_token"]
if store_token is None or store_token == False:
    os.remove(TOKEN_PATH)