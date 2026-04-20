import gmail_client as client, utils, config as cfg, email_utils, nli_model
import json

MIN_SCORE = 0.55
DEFAULT_CATEGORY = {
    "name": "Default", # overrideable
    "description": "All emails that could not be reliably put into a given category"
}

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
            "description": desc,
            "vector": current.get("vector") or []
        })

    cfg.saveToFile(cfg.CATEGORIES_KEY, merged)
    cfg.load_categories()

    
# returns dict[id -> vec]
def get_category_vectors():
    categories = cfg.get_categories()
    vectors = {}
    should_cache = cfg.get_main()["optimizations"].get("cache_category_vectors", False)
    changed = False
    for cat in categories:
        foreign_id = cat.get("foreign_id")
        if not foreign_id:
            print(f"skipping category without mailbox id: {cat.get('name')}")
            continue

        vec = cat.get("vector")
        if not (should_cache and vec):
            print("embedding cat: " + cat["name"])
            vec = embed_category(prepare_category_embed(cat))
            if should_cache:
                cat["vector"] = vec
                changed = True

        vectors[foreign_id] = vec

    if should_cache and changed:
        cfg.saveToFile(cfg.CATEGORIES_KEY, categories)
    return vectors

def prepare_category_embed(cat):
    return cat["name"]+". "+cat["description"]

# returns id of best match / -1 for no confident match
def compare_against_categories(email_vec, default_label_id):
    global categories
    bestMatch = {
        "id": default_label_id,
        "score": MIN_SCORE
    }

    for id, vec in categories.items():
        cos_score = None#model.cos(email_vec, vec)
        
        print(id + ": " + str(cos_score))
        if cos_score > bestMatch["score"]:
            bestMatch["id"] = id
            bestMatch["score"] = cos_score
            print("best match: "+id)

    #print(bestMatch)
    return bestMatch

def embed_category(desc):
    #return model.embed(utils.prepare_passage(desc))
    pass
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

# TODO validate config
cfg.load_main()
cfg.load_categories()

client.load_credentials()
client.create_mailbox_if_not_exists()
update_categories()

"""
categories = get_category_vectors()
default_label_id = client.get_label_id(cfg.get_main().get("default_category_name"))
if not default_label_id:
    raise RuntimeError("Default category label does not exist.")
managed_label_ids = get_managed_label_ids()

ids = client.list_unread_from_inbox()
emails = client.load_cleaned_emails(ids)
import json
print(json.dumps(emails, indent=4))

for id, email in emails.items():
    vec = model.embed(utils.prepare_query(email))
    print(np.linalg.norm(vec))
    print("\n\n-------------------")
    print(email["subject"])
    category = compare_against_categories(vec, default_label_id)
    # TODO log the result
    client.move_to_mailbox(id, category["id"], remove_label_ids=managed_label_ids)
"""

# ------------------ NLI pipeline--------------------

default_label_name = cfg.get_main().get("default_category_name")
default_label_id = client.get_label_id(default_label_name)
if not default_label_id:
    raise RuntimeError("Default category label does not exist.")

managed_label_ids = get_managed_label_ids()
configured_categories = cfg.get_categories() or []

ids = client.list_unread_from_inbox()
emails = client.load_cleaned_emails(ids)
print(json.dumps(emails, indent=4))

nli_model.load_model()

for id, email in emails.items():
    sequence = nli_model.format_email_for_nli(email)

    print("\n\n-------------------")
    print(email.get("subject", "<no subject>"))

    prediction = nli_model.predict_best_category(sequence, configured_categories)
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
