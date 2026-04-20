from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


MODEL_NAME = "facebook/bart-large-mnli"
CACHE_DIR = Path("models")
DEFAULT_HYPOTHESIS_TEMPLATE = "This email belongs to the category: {}."

_tokenizer = None
_model = None
_device = None


@dataclass(frozen=True)
class NLIScore:
    label: str
    score: float
    entailment: float
    neutral: float
    contradiction: float
    hypothesis: str


@dataclass(frozen=True)
class CategoryPrediction:
    category_name: str
    category_description: str
    score: float
    entailment: float
    neutral: float
    contradiction: float
    hypothesis: str


def get_device():
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def is_loaded() -> bool:
    return _model is not None and _tokenizer is not None


def load_model(model_name: str = MODEL_NAME, cache_dir: Path = CACHE_DIR):
    global _model, _tokenizer

    if is_loaded():
        return _model, _tokenizer

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    _tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_path))
    _model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        cache_dir=str(cache_path)
    )
    _model.to(get_device())
    _model.eval()
    return _model, _tokenizer


def unload_model():
    global _model, _tokenizer, _device

    _model = None
    _tokenizer = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    _device = None


def get_label_mapping():
    model, _ = load_model()
    id_to_label = model.config.id2label
    return {idx: value.lower() for idx, value in id_to_label.items()}


def _get_label_index(target: str) -> int:
    for idx, name in get_label_mapping().items():
        if name == target:
            return idx
    raise ValueError(f"Could not find '{target}' label in model config.")


def get_entailment_index() -> int:
    return _get_label_index("entailment")


def get_neutral_index() -> int:
    return _get_label_index("neutral")


def get_contradiction_index() -> int:
    return _get_label_index("contradiction")


def normalize_text(value: str) -> str:
    return " ".join((value or "").split())


def format_email_for_nli(email: dict) -> str:
    parts = []

    sender = normalize_text(email.get("from"))
    subject = normalize_text(email.get("subject"))
    body = normalize_text(email.get("body"))

    if sender:
        parts.append(f"From: {sender}")
    if subject:
        parts.append(f"Subject: {subject}")
    if body:
        parts.append(f"Body: {body}")

    return "\n".join(parts)


def build_label_hypothesis(label: str, hypothesis_template: str = DEFAULT_HYPOTHESIS_TEMPLATE) -> str:
    clean_label = normalize_text(label)
    if not clean_label:
        raise ValueError("Label must not be empty.")
    return hypothesis_template.format(clean_label)


def build_category_hypothesis(category: dict) -> str:
    name = normalize_text(category.get("name"))
    description = normalize_text(category.get("description"))

    if not name:
        raise ValueError("Category must have a non-empty name.")

    if description:
        return f"This email belongs to the category '{name}'. {description}"
    return build_label_hypothesis(name)


def _softmax_logits(logits: torch.Tensor) -> torch.Tensor:
    return torch.softmax(logits, dim=-1)


@torch.inference_mode()
def score_hypothesis(sequence: str, hypothesis: str) -> dict:
    if not sequence or not hypothesis:
        raise ValueError("Both sequence and hypothesis are required.")

    model, tokenizer = load_model()
    encoded = tokenizer(
        sequence,
        hypothesis,
        return_tensors="pt",
        truncation="only_first",
        max_length=tokenizer.model_max_length
    )
    encoded = {key: value.to(get_device()) for key, value in encoded.items()}

    logits = model(**encoded).logits[0]
    probabilities = _softmax_logits(logits).detach().cpu()

    entailment = float(probabilities[get_entailment_index()].item())
    neutral = float(probabilities[get_neutral_index()].item())
    contradiction = float(probabilities[get_contradiction_index()].item())

    return {
        "entailment": entailment,
        "neutral": neutral,
        "contradiction": contradiction,
        "score": entailment
    }


def score_candidate_labels(
    sequence: str,
    candidate_labels: Iterable[str],
    hypothesis_template: str = DEFAULT_HYPOTHESIS_TEMPLATE
) -> list[NLIScore]:
    results = []

    for label in candidate_labels:
        hypothesis = build_label_hypothesis(label, hypothesis_template=hypothesis_template)
        probs = score_hypothesis(sequence, hypothesis)
        results.append(NLIScore(
            label=label,
            score=probs["score"],
            entailment=probs["entailment"],
            neutral=probs["neutral"],
            contradiction=probs["contradiction"],
            hypothesis=hypothesis
        ))

    return sorted(results, key=lambda item: item.score, reverse=True)


def predict_best_label(
    sequence: str,
    candidate_labels: Iterable[str],
    hypothesis_template: str = DEFAULT_HYPOTHESIS_TEMPLATE
) -> NLIScore | None:
    ranked = score_candidate_labels(
        sequence,
        candidate_labels,
        hypothesis_template=hypothesis_template
    )
    if not ranked:
        return None
    return ranked[0]


def score_categories(sequence: str, categories: Iterable[dict]) -> list[CategoryPrediction]:
    results = []

    for category in categories:
        hypothesis = build_category_hypothesis(category)
        probs = score_hypothesis(sequence, hypothesis)
        results.append(CategoryPrediction(
            category_name=category.get("name", ""),
            category_description=category.get("description", ""),
            score=probs["score"],
            entailment=probs["entailment"],
            neutral=probs["neutral"],
            contradiction=probs["contradiction"],
            hypothesis=hypothesis
        ))

    return sorted(results, key=lambda item: item.score, reverse=True)


def predict_best_category(sequence: str, categories: Iterable[dict]) -> CategoryPrediction | None:
    ranked = score_categories(sequence, categories)
    if not ranked:
        return None
    return ranked[0]
