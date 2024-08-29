from openai import OpenAI
import numpy as np

client = OpenAI()

def test_closest_n_embedding_matches():
    target = "It's not a big deal."
    candidates = [
        "I think he just made it up.",
        "You can easily make it up.",
        "This isn't a significant issue.",
        "It's not important.",
        "We need to figure this out quickly."
    ]
    top_n_matches = closest_n_embedding_matches(target, candidates, n=3)
    print(f"Top 3 closest matches: {top_n_matches}")

def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

def cosine_similarity(embedding1, embedding2):
    """
    Calculate the cosine similarity between two embeddings.

    Args:
    - embedding1, embedding2 (list): Two embeddings to compare.

    Returns:
    - float: The cosine similarity score.
    """
    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    return dot_product / (norm1 * norm2)

def closest_n_embedding_matches(target_string, candidate_strings, n=3, model='text-embedding-3-small'):
    """
    Finds the n closest matching strings from a list based on cosine similarity of embeddings.
    
    Args:
    - target_string (str): The string to match against.
    - candidate_strings (list): A list of strings to compare to the target string.
    - n (int): The number of closest matches to return. Default is 3.
    - model (str): The model to use for generating embeddings. Default is 'text-embedding-3-small'.
    
    Returns:
    - list: A list of tuples where each tuple contains a candidate string and its similarity score.
    """
    # Get embedding for the target string
    target_embedding = get_embedding(target_string, model=model)
    
    # Calculate similarities
    similarities = []
    for candidate in candidate_strings:
        candidate_embedding = get_embedding(candidate, model=model)
        similarity = cosine_similarity(target_embedding, candidate_embedding)
        similarities.append((candidate, similarity))
    
    # Sort candidates by similarity in descending order and get the top n matches
    top_matches = sorted(similarities, key=lambda x: x[1], reverse=True)[:n]
    
    return top_matches


