from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

# Test cases
test_pairs = [
    ("Islamic banking infrastructure", "sukuk issuance capabilities"),  # Should be HIGH
    ("preventive healthcare", "hospital emergency capacity"),           # Should be LOW
    ("implement carbon tax", "reject carbon tax"),                      # Should be MEDIUM-LOW
    ("vaccination programs", "immunization campaigns"),                 # Should be HIGH
]

for text1, text2 in test_pairs:
    embeddings = model.encode([text1, text2])
    similarity = np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    )
    normalized = (similarity + 1) / 2
    print(f"Similarity: {normalized:.3f} | '{text1}' ↔ '{text2}'")
