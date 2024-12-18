import os
import json
import pprint
from datetime import datetime

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


def register_cm_image_variants_request(project_dir, page, description_index, image_index, userid):
    """
    The user is requesting new variants for a given image.
    If image_index might be optional (e.g. requesting variants from the base description), 
    you can allow image_index=None or treat missing image_index as a special case.
    """
    data = load_community_feedback(project_dir, page)

    new_request = {
        "user_id": userid,
        "description_index": description_index,
        "image_index": image_index,
        "timestamp": current_timestamp()
    }
    data["variants_requests"].append(new_request)

    save_community_feedback(project_dir, page, data)


def register_cm_image_advice(project_dir, page, description_index, advice_text, userid):
    """
    Associates advice with a given description (not specific image).
    """
    data = load_community_feedback(project_dir, page)

    new_advice = {
        "user_id": userid,
        "description_index": description_index,
        "text": advice_text,
        "timestamp": current_timestamp()
    }
    data["advice"].append(new_advice)

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
    Returns all advice and variants requests related to a particular description.
    Variant requests may or may not require image_index, depending on your use case.
    """
    description_index = int(description_index)
    
    data = load_community_feedback(project_dir, page)

    description_advice = [a for a in data["advice"] if a["description_index"] == description_index]
    description_variants_requests = [r for r in data["variants_requests"]
                                     if r["description_index"] == description_index]

    return {
        "advice": description_advice,
        "variants_requests": description_variants_requests
    }
