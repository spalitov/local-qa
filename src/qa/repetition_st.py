from __future__ import annotations
from typing import Dict, List, Tuple
import re
import numpy as np
from sentence_transformers import SentenceTransformer

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]

def cosine_sim_matrix(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    A_norm = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
    B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
    return A_norm @ B_norm.T

def repetition_check(
    model: SentenceTransformer,
    prior_agent_texts: List[str],
    audited_agent_text: str,
) -> Tuple[float, List[Dict]]:
    prior_sents: List[str] = []
    for t in prior_agent_texts:
        prior_sents.extend(split_sentences(t))

    audited_sents = split_sentences(audited_agent_text)

    if not prior_sents or not audited_sents:
        return 0.0, []

    prior_emb = model.encode(prior_sents, convert_to_numpy=True, normalize_embeddings=False)
    aud_emb = model.encode(audited_sents, convert_to_numpy=True, normalize_embeddings=False)

    sim = cosine_sim_matrix(aud_emb, prior_emb)
    max_sim = float(sim.max())

    hit_examples: List[Dict] = []
    for i in range(sim.shape[0]):
        j = int(sim[i].argmax())
        hit_examples.append(
            {
                "audited_sentence": audited_sents[i],
                "matched_prior_sentence": prior_sents[j],
                "cosine": float(sim[i][j]),
            }
        )
    hit_examples.sort(key=lambda x: x["cosine"], reverse=True)
    return max_sim, hit_examples[:3]
