import os
import json
import asyncio
import pprint
from pathlib import Path
from datetime import datetime

from .clara_coherent_images_alternate import get_alternate_images_json
from .clara_coherent_images_utils import score_for_image_dir, get_pages

def community_feedback_path(project_dir, page):
    return os.path.join(project_dir, "pages", f"page{page}", "community_feedback.json")

def load_community_feedback(project_dir, page):
    path = community_feedback_path(project_dir, page)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # If no file exists, return an empty structure
        return {
            "votes": [],
            "advice": [],
            "comments": [],
            "variants_requests": []
        }

def save_community_feedback(project_dir, page, data):
    path = community_feedback_path(project_dir, page)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def current_timestamp():
    return datetime.utcnow().isoformat()

def register_cm_image_vote(project_dir, page, description_index, image_index, vote_type, userid):
    """
    vote_type: "upvote" or "downvote"
    """
    data = load_community_feedback(project_dir, page)

    # Check if user already voted for this image
    existing_vote = None
    for vote in data["votes"]:
        if (vote["user_id"] == userid and 
            vote["description_index"] == description_index and 
            vote["image_index"] == image_index):
            existing_vote = vote
            break

    if existing_vote:
        # If already voted, update the vote_type if different
        if existing_vote["vote_type"] != vote_type:
            existing_vote["vote_type"] = vote_type
            existing_vote["timestamp"] = current_timestamp()
    else:
        # No previous vote, append a new record
        new_vote = {
            "user_id": userid,
            "description_index": description_index,
            "image_index": image_index,
            "vote_type": vote_type,
            "timestamp": current_timestamp()
        }
        data["votes"].append(new_vote)

    save_community_feedback(project_dir, page, data)


def register_cm_image_variants_request(project_dir, page, description_index, userid):
    """
    The user is requesting new variants for a given image grouè.
    """
    data = load_community_feedback(project_dir, page)

    new_request = {
        "user_id": userid,
        "description_index": description_index,
        "timestamp": current_timestamp()
    }
    data["variants_requests"].append(new_request)

    save_community_feedback(project_dir, page, data)


def register_cm_page_advice(project_dir, page, advice_text, userid):
    """
    Associates advice with the *entire page*, not a specific description or image.
    """
    data = load_community_feedback(project_dir, page)

    new_advice = {
        "user_id": userid,
        "text": advice_text,
        "timestamp": current_timestamp()
    }
    data["advice"].append(new_advice)

    add_indices_to_advice(data["advice"])

    save_community_feedback(project_dir, page, data)


def get_cm_image_info(project_dir, page, description_index, image_index):
    """
    Returns all votes and comments related to a specific image.
    Comments not included in your original specification steps but were in previous examples.
    If comments are needed, we handle them similarly to votes.
    """
    description_index = int(description_index)
    image_index = int(image_index)
    
    data = load_community_feedback(project_dir, page)

    image_votes = [v for v in data["votes"] 
                   if v["description_index"] == description_index and v["image_index"] == image_index]
    image_comments = [c for c in data["comments"]
                      if c["description_index"] == description_index and c["image_index"] == image_index]

    return {
        "votes": image_votes,
        "comments": image_comments
    }


def get_cm_description_info(project_dir, page, description_index):
    """
    Returns all variants requests related to a particular description.
    Variant requests may or may not require image_index, depending on your use case.
    """
    description_index = int(description_index)
    
    data = load_community_feedback(project_dir, page)

    description_variants_requests = [r for r in data["variants_requests"]
                                     if r["description_index"] == description_index]

    return { "variants_requests": description_variants_requests }

def get_cm_page_advice(project_dir, page):
    """
    Returns all advice related to a particular page.
    """
    
    data = load_community_feedback(project_dir, page)

    add_indices_to_advice(data["advice"])

    save_community_feedback(project_dir, page, data)

    return data['advice']


def update_ai_votes_in_feedback(project_dir, page_number):
    """
    Update AI votes in the community_feedback.json for a given page.

    Args:
        project_dir (str): The project directory.
        page_number (int): The page number.
        params (dict): Parameters containing project configuration.

    Returns:
        None
    """
    params =  { 'project_dir': project_dir }
    content_dir = Path(project_dir) / f"pages/page{page_number}"
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Load existing feedback
    feedback_data = load_community_feedback(project_dir, page_number)

    votes = feedback_data.get('votes', [])

    for img in alternate_images:
        description_index = int(img['description_index'])
        image_index = int(img['image_index'])

        # Check if AI vote is already recorded
        ai_votes = [v for v in votes if v['description_index'] == description_index and v['image_index'] == image_index and v['user_id'] == 'AI']
        if ai_votes:
            continue  # AI vote already recorded, skip

        # Get AI score for the image
        image_dir = content_dir / f"description_v{description_index}" / f"image_v{image_index}"
        ai_score, _ = score_for_image_dir(image_dir, params)

        # Map AI score to vote type
        if ai_score in [3, 4]:
            vote_type = 'upvote'
        elif ai_score in [0, 1]:
            vote_type = 'downvote'
        else:
            vote_type = 'neutral'

        # Add AI vote to feedback
        if vote_type != 'neutral':
            ai_vote_record = { "user_id": "AI",
                               "description_index": description_index,
                               "image_index": image_index,
                               "vote_type": vote_type,
                               "timestamp": current_timestamp()
                               }
            votes.append(ai_vote_record)

    # Write updated feedback to file
    save_community_feedback(project_dir, page_number, feedback_data)
    

def determine_preferred_image(content_dir, project_dir, page_number):
    """
    Determine the preferred image for a page based on combined AI and human votes.

    Args:
        content_dir (Path): Path to the content directory.
        project_dir (str): Path to the project directory.
        page_number (int): Page number.

    Returns:
        int: The `alternate_image_id` of the preferred image, or None if no images exist.
    """
    feedback_data = load_community_feedback(project_dir, page_number)
    votes = feedback_data.get('votes', [])
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Tally votes for each image
    vote_counts = {}
    for img in alternate_images:
        if not img['hidden']:
            image_id = img['id']
            description_index = int(img['description_index'])
            image_index = int(img['image_index'])
            relevant_votes = [v for v in votes if v['description_index'] == description_index and v['image_index'] == image_index]

            upvotes = sum(1 for v in relevant_votes if v['vote_type'] == 'upvote')
            downvotes = sum(1 for v in relevant_votes if v['vote_type'] == 'downvote')
            vote_counts[image_id] = upvotes - downvotes  # Net score

    # Find the image with the highest net score
    preferred_image_id = max(vote_counts, key=vote_counts.get, default=None)

    return preferred_image_id

def add_indices_to_advice(advice_list):
    """
    Add indices to advice. Advice items will not change, so this is safe.
    """
    
    index = 1
    for item in advice_list:
        item['index'] = index
        index += 1

def get_all_cm_requests(project_dir):
    params = { 'project_dir': project_dir }
    pages = get_pages(params)
    requests = []

    for page in pages:
        requests.extend(get_all_cm_requests_for_page(project_dir, page))

    return requests

def get_all_cm_requests_for_page(project_dir, page):
    requests = []
                        
    data = load_community_feedback(project_dir, page)
    
    advice_list = data['advice']
    add_indices_to_advice(advice_list)
    for item in advice_list:
        request = { 'request_type': 'advice',
                    'page': page,
                    'index': item['index'],
                    'status': item['status'] if 'status' in item else 'submitted',
                    }
        requests.append(request)

    variants_requests_list = data['variants_requests']
    for item in variants_requests_list:
        request = { 'request_type': 'variants_requests',
                    'page': page,
                    'description_index': item['description_index'],
                    'status': item['status'] if 'status' in item else 'submitted',
                    }
        requests.append(request)

    return requests
        

def set_cm_request_status(project_dir, request_item, status):
    """
    Sets the status on a piece of advice
    """

    request_type = request_item['request_type']
    page_number = request_item['page']

    data = load_community_feedback(project_dir, page_number)

    if request_type == 'variants_requests':
        description_index = request_item['description_index']
        for item in data['variants_requests']:
            if item['description_index'] == description_index:
                item['status'] = status
    elif request_type == 'advice':
        index = request_item['index']
        for item in data['advice']:
            if item['index'] == index:
                item['status'] = status

    save_community_feedback(project_dir, page_number, data)

    
