from .clara_utils import file_exists, read_json_file, write_json_to_file

import nltk
from nltk import pos_tag, word_tokenize
from nltk.util import ngrams
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Ensure NLTK data is downloaded
nltk.download('averaged_perceptron_tagger_eng')
nltk.download('punkt')

cache_file = '$CLARA/tmp/pos_ngram_cache.json'

if file_exists(cache_file):
    pos_ngram_cache = read_json_file(cache_file)
else:
    pos_ngram_cache = {}

def save_pos_ngram_cache_to_file():
    """Save the current cache to a file."""
    write_json_to_file(pos_ngram_cache, cache_file)

def get_pos_tags(text):
    """
    Tokenizes and applies POS tagging to the input text.

    Parameters:
    - text: str, the input text.

    Returns:
    - A list of POS tags.
    """
    tokens = word_tokenize(text)
    pos_tags = pos_tag(tokens)
    return [tag for _, tag in pos_tags]

def generate_pos_ngrams(pos_tags, n=2):
    """
    Generates n-grams of POS tags.

    Parameters:
    - pos_tags: list, the POS tags.
    - n: int, the number of grams.

    Returns:
    - A list of n-grams.
    """
    return list(ngrams(pos_tags, n))

def create_sparse_vector_from_ngrams(ngrams_list):
    """
    Converts a list of n-grams into a sparse vector using CountVectorizer.

    Parameters:
    - ngrams_list: list, the n-grams.

    Returns:
    - A sparse vector representing the n-gram counts.
    """
    # Check if ngrams_list is empty, return a default empty vector if so
    if not ngrams_list:
        return np.zeros((1, 1)), None  # Return an empty vector with no features
    
    vectorizer = CountVectorizer(tokenizer=lambda x: x, preprocessor=lambda x: x, token_pattern=None)
    ngram_strs = [" ".join(ngram) for ngram in ngrams_list]
    vector = vectorizer.fit_transform([ngram_strs])
    return vector.toarray(), vectorizer

##def get_weighted_pos_ngram_vector(text, ngram_ranges=[2, 3, 4], weights=[1, 4, 9]):
##    """
##    Generate a single weighted sparse vector of POS n-gram counts for a given text.
##    
##    Parameters:
##    - text: str, input text to vectorize.
##    - ngram_ranges: list of int, n-gram lengths to consider.
##    - weights: list of int, weights to assign to each n-gram length.
##    
##    Returns:
##    - A weighted sparse vector for the input text.
##    """
##
##    # Normalize text to ensure consistency in cache lookups
##    normalized_text = text.replace("\n", " ")
##
##    # Check if POS n-gram vector is already cached
##    if normalized_text in pos_ngram_cache:
##        return np.array(pos_ngram_cache[normalized_text])
##    
##    pos_tags = get_pos_tags(normalized_text)
##
##    # Early exit if the text is too short or has no POS tags
##    if len(pos_tags) < 2:
##        return np.zeros((1, 1))  # Return a default empty vector
##    
##    weighted_vector = np.zeros((1,))
##
##    for n, weight in zip(ngram_ranges, weights):
##        pos_ngrams = generate_pos_ngrams(pos_tags, n)
##        sparse_vector, _ = create_sparse_vector_from_ngrams(pos_ngrams)
##        
##        if weighted_vector.size == 1:  # Initialize on the first pass
##            weighted_vector = weight * sparse_vector
##        else:
##            if weighted_vector.shape[1] < sparse_vector.shape[1]:
##                # Extend weighted_vector to match the new sparse_vector size
##                new_vector = np.zeros((1, sparse_vector.shape[1]))
##                new_vector[:, :weighted_vector.shape[1]] = weighted_vector
##                weighted_vector = new_vector
##
##            # Weight and add to the existing vector
##            weighted_vector[:, :sparse_vector.shape[1]] += weight * sparse_vector
##
##    # Convert to list for JSON serialization and cache it
##    pos_ngram_cache[normalized_text] = weighted_vector.tolist()
##    save_pos_ngram_cache_to_file()
##
##    return weighted_vector

def get_weighted_pos_ngram_vector(text, ngram_ranges=[2, 3, 4], weights=[1, 4, 9]):
    """
    Generate a single weighted sparse vector of POS n-gram counts for a given text.
    
    Parameters:
    - text: str, input text to vectorize.
    - ngram_ranges: list of int, n-gram lengths to consider.
    - weights: list of int, weights to assign to each n-gram length.
    
    Returns:
    - A weighted sparse vector for the input text.
    """

    # Normalize text to ensure consistency in cache lookups
    normalized_text = text.replace("\n", " ")

    # Check if POS n-gram vector is already cached
    if normalized_text in pos_ngram_cache:
        return np.array(pos_ngram_cache[normalized_text])
    
    pos_tags = get_pos_tags(normalized_text)
    weighted_vector = np.zeros((1,), dtype=np.float64)  # Initialize as float64

    for n, weight in zip(ngram_ranges, weights):
        pos_ngrams = generate_pos_ngrams(pos_tags, n)
        sparse_vector, _ = create_sparse_vector_from_ngrams(pos_ngrams)

        if weighted_vector.size == 1:  # Initialize on the first pass
            weighted_vector = weight * sparse_vector.astype(np.float64)  # Convert sparse vector to float64
        else:
            if weighted_vector.shape[1] < sparse_vector.shape[1]:
                # Extend weighted_vector to match the new sparse_vector size
                new_vector = np.zeros((1, sparse_vector.shape[1]), dtype=np.float64)
                new_vector[:, :weighted_vector.shape[1]] = weighted_vector
                weighted_vector = new_vector

            # Weight and add to the existing vector, ensuring dtype consistency
            weighted_vector[:, :sparse_vector.shape[1]] += weight * sparse_vector.astype(np.float64)

    # Convert to list for JSON serialization and cache it
    pos_ngram_cache[normalized_text] = weighted_vector.tolist()
    save_pos_ngram_cache_to_file()

    return weighted_vector


def pad_vectors_to_same_length(vec1, vec2):
    """
    Pads two vectors to ensure they have the same length.
    
    Parameters:
    - vec1, vec2: np.ndarray, input vectors.
    
    Returns:
    - Two np.ndarray of the same length.
    """
    max_len = max(vec1.shape[1], vec2.shape[1])

    # Pad vec1 if needed
    if vec1.shape[1] < max_len:
        padded_vec1 = np.zeros((1, max_len))
        padded_vec1[:, :vec1.shape[1]] = vec1
    else:
        padded_vec1 = vec1

    # Pad vec2 if needed
    if vec2.shape[1] < max_len:
        padded_vec2 = np.zeros((1, max_len))
        padded_vec2[:, :vec2.shape[1]] = vec2
    else:
        padded_vec2 = vec2

    return padded_vec1, padded_vec2

def pos_based_similarity(text1, text2, ngram_ranges=[2, 3, 4], weights=[1, 4, 9]):
    vector1 = get_weighted_pos_ngram_vector(text1, ngram_ranges, weights)
    vector2 = get_weighted_pos_ngram_vector(text2, ngram_ranges, weights)

    # If either vector is the default empty vector, return a similarity of 0.0
    if vector1.shape[1] == 1 or vector2.shape[1] == 1:
        return 0.0

    # Pad vectors to the same length
    padded_vector1, padded_vector2 = pad_vectors_to_same_length(vector1, vector2)

    # Calculate cosine similarity
    similarity = cosine_similarity(padded_vector1, padded_vector2)[0][0]
    return similarity

def test_weighted_pos_based_similarity():
    text1 = "She enjoys playing tennis on weekends."
    text2 = "He likes playing soccer on Saturdays."
    text3 = "The quick brown fox jumps over the lazy dog."

    print(f"Similarity between text1 and text2: {pos_based_similarity(text1, text2)}")
    print(f"Similarity between text1 and text3: {pos_based_similarity(text1, text3)}")
