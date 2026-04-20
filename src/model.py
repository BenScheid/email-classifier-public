from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download
from transformers import AutoModel, AutoTokenizer
import torch
import numpy as np
import os
from pathlib import Path

MODEL_NAME = "intfloat/e5-large-v2"
# MODEL_VERSION = "v2.2.0"
CACHE_DIR = Path("models") 

local_model_path = snapshot_download(
    repo_id=f"{MODEL_NAME}",
    cache_dir=str(CACHE_DIR)
)

model = SentenceTransformer(local_model_path)

print(model._version)

def embed(text:str):
    return model.encode(text, normalize_embeddings=True)

def cos(a, b):
    return float(np.dot(a,b))
# [4, 4]"""