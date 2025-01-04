import os
import json
import asyncio
import pprint
from pathlib import Path
from datetime import datetime

from .clara_coherent_images_alternate import get_alternate_images_json
from .clara_coherent_images_utils import score_for_image_dir, element_score_for_description_dir
from .clara_coherent_images_utils import get_pages, project_pathname, read_project_json_file
from .clara_utils import file_exists

def get_page_overview_info_for_cm_reviewing(project_dir):
    # Load story data
    story_data = read_project_json_file(project_dir, 'story.json')
    pages_info = []

    if story_data:
        for page in story_data:
            page_number = page['page_number']
            page_text = page.get('text', '').strip()
            original_page_text = page.get('original_page_text', '').strip()

            # Take a short excerpt of page_text for display
            excerpt_length = 100
            excerpt = (page_text[:excerpt_length] + '...') if len(page_text) > excerpt_length else page_text
            original_text_excerpt = (original_page_text[:excerpt_length] + '...') if len(original_page_text) > excerpt_length else original_page_text

            # Make sure the preferred image is up to date
##            content_dir = project_pathname(project_dir, f'pages/page{page_number}')
##            preferred_image_id = determine_preferred_image(content_dir, project_dir, page_number)
##            if preferred_image_id is not None:
##                clara_project_internal.promote_v2_page_image(page_number, preferred_image_id)

            # Try to find a main image for the page
            relative_page_image_path = f'pages/page{page_number}/image.jpg'
            page_image_path = project_pathname(project_dir, relative_page_image_path)
            page_image_exists = file_exists(page_image_path)

            requests_for_page = get_all_cm_requests_for_page(project_dir, page_number)
            requests_exist_for_page = ( len([ request for request in requests_for_page if request['status'] == 'submitted' ]) != 0 )

            pages_info.append({
                'page_number': page_number,
                'excerpt': excerpt,
                'original_text_excerpt': original_text_excerpt,
                'relative_page_image_path': ( relative_page_image_path if page_image_exists else None ),
                'requests_exist_for_page': requests_exist_for_page,
            })
    else:
        # No story data means no pages
        pass

    return pages_info

def get_page_description_info_for_cm_reviewing(cm_or_co, alternate_images, page_number, project_dir):
    content_dir = project_pathname(project_dir, f"pages/page{page_number}")

    preferred_image_id = determine_preferred_image(content_dir, project_dir, page_number)

    # Group images by description_index
    images_by_description = {}
    for img in alternate_images:
        d_idx = img['description_index']
        if d_idx not in images_by_description:
            images_by_description[d_idx] = []
        images_by_description[d_idx].append(img)

    # For each description, get variants requests, and votes
    descriptions_info = {}
    for d_idx, imgs in images_by_description.items():
        desc_info = get_cm_description_info(project_dir, page_number, d_idx)
        # If we're in the CO view, we show the hidden images with a red border
        non_hidden_imgs = [ img for img in imgs if not img['hidden'] ] if cm_or_co == 'cm' else imgs
        if non_hidden_imgs:
            for img_info in non_hidden_imgs:
                i_idx = img_info['image_index']
                img_feedback = get_cm_image_info(project_dir, page_number, d_idx, i_idx)
                img_info['votes'] = img_feedback['votes']
                upvotes = sum(1 for v in img_feedback['votes'] if v['vote_type'] == 'upvote')
                downvotes = sum(1 for v in img_feedback['votes'] if v['vote_type'] == 'downvote')
                img_info['upvotes_count'] = upvotes
                img_info['downvotes_count'] = downvotes

                # Determine if this is the preferred image
                img_info['preferred'] = img_info['id'] == preferred_image_id
                
            descriptions_info[d_idx] = {
                'variants_requests': desc_info['variants_requests'],
                'images': non_hidden_imgs
            }
            
    return descriptions_info, preferred_image_id

def get_element_description_info_for_cm_reviewing(alternate_images, element_name, project_dir):
    content_dir = project_pathname(project_dir, f"elements/{element_name}")

    # Adapt determine_preferred_element_description from
    # determine_preferred_image
    preferred_description_id = determine_preferred_element_description(content_dir, project_dir, element_name)

    # Group images by description_index
    images_by_description = {}
    for img in alternate_images:
        d_idx = img['description_index']
        if d_idx not in images_by_description:
            images_by_description[d_idx] = []
        images_by_description[d_idx].append(img)

    # For each description, get variants requests, and votes
    descriptions_info = {}
    for d_idx, imgs in images_by_description.items():
        desc_info = get_cm_description_info_for_element(project_dir, element_name, d_idx)
        upvotes = sum(1 for v in desc_info['votes'] if v['vote_type'] == 'upvote')
        downvotes = sum(1 for v in desc_info['votes'] if v['vote_type'] == 'downvote')

        # Determine if this is the preferred description
        preferred = ( d_idx == preferred_description_id )
            
        descriptions_info[d_idx] = {
            'upvotes_count': upvotes,
            'downvotes_count': downvotes,
            'preferred': preferred,
            'images': imgs,
        }
            
    return descriptions_info, preferred_description_id

def community_feedback_path(project_dir, page):
    return os.path.join(project_dir, "pages", f"page{page}", "community_feedback.json")

def community_feedback_path_for_element(project_dir, element_name):
    return os.path.join(project_dir, "elements", f"{element_name}", "community_feedback.json")

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

def load_community_feedback_for_element(project_dir, element_name):
    path = community_feedback_path_for_element(project_dir, element_name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # If no file exists, return an empty structure
        return {
            "votes": [],
            "advice": [],
            "comments": []
        }

def save_community_feedback(project_dir, page, data):
    path = community_feedback_path(project_dir, page)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_community_feedback_for_element(project_dir, element_name, data):
    path = community_feedback_path_for_element(project_dir, element_name)
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

def register_cm_element_vote(project_dir, element_name, description_index, vote_type, userid):
    """
    vote_type: "upvote" or "downvote"
    """
    data = load_community_feedback_for_element(project_dir, element_name)

    # Check if user already voted for this image
    existing_vote = None
    for vote in data["votes"]:
        if (vote["user_id"] == userid and 
            vote["description_index"] == description_index): 
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
            "vote_type": vote_type,
            "timestamp": current_timestamp()
        }
        data["votes"].append(new_vote)

    save_community_feedback_for_element(project_dir, element_name, data)
    

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

def get_cm_description_info_for_element(project_dir, element_name, description_index):
    """
    Returns all votes related to a particular description.
    """
    description_index = int(description_index)
    
    data = load_community_feedback_for_element(project_dir, element_name)

    votes = [r for r in data["votes"]
             if r["description_index"] == description_index]

    return { "votes": votes }

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

def update_ai_votes_for_element_in_feedback(project_dir, element_name):
    """
    Update AI votes in the community_feedback.json for a given element.

    Args:
        project_dir (str): The project directory.
        element_name (str): The element name.

    Returns:
        None
    """
    params =  { 'project_dir': project_dir }
    content_dir = Path(project_dir) / f"elements/{element_name}"
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Load existing feedback
    # Adapt load_community_feedback_for_element from
    # load_community_feedback
    feedback_data = load_community_feedback_for_element(project_dir, element_name)

    votes = feedback_data.get('votes', [])

    for img in alternate_images:
        description_index = int(img['description_index'])

        # Check if AI vote is already recorded
        ai_votes = [v for v in votes if v['description_index'] == description_index and v['user_id'] == 'AI']
        if ai_votes:
            continue  # AI vote already recorded, skip

        # Get AI score for the image
        description_dir = content_dir / f"description_v{description_index}"
        # Adapt element_score_for_description_dir
        # from clara_coherent_images_utils.score_for_image_dir
        ai_score = element_score_for_description_dir(description_dir, params)

        # Map AI score to vote type
        if ai_score >= 2.5:
            vote_type = 'upvote'
        elif ai_score < 2.0:
            vote_type = 'downvote'
        else:
            vote_type = 'neutral'

        # Add AI vote to feedback
        if vote_type != 'neutral':
            ai_vote_record = { "user_id": "AI",
                               "description_index": description_index,
                               "vote_type": vote_type,
                               "timestamp": current_timestamp()
                               }
            votes.append(ai_vote_record)

    # Write updated feedback to file
    # Adapt save_community_feedback_for_element
    # from save_community_feedback
    save_community_feedback_for_element(project_dir, element_name, feedback_data)
    
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

def determine_preferred_element_description(content_dir, project_dir, element_name):
    """
    Determine the preferred description index for an element based on combined AI and human votes.

    Args:
        content_dir (Path): Path to the content directory.
        project_dir (str): Path to the project directory.
        element_name (str): Element name.

    Returns:
        int: The index of the preferred description directory, or None if no description directories exist.
    """
    feedback_data = load_community_feedback_for_element(project_dir, element_name)
    votes = feedback_data.get('votes', [])
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Tally votes for each image
    vote_counts = {}
    for img in alternate_images:
        description_index = int(img['description_index'])
        if not description_index in vote_counts:
            # Only count a description index once
            relevant_votes = [v for v in votes if v['description_index'] == description_index]

            upvotes = sum(1 for v in relevant_votes if v['vote_type'] == 'upvote')
            downvotes = sum(1 for v in relevant_votes if v['vote_type'] == 'downvote')
            vote_counts[description_index] = upvotes - downvotes  # Net score

    # Find the description index with the highest net score
    preferred_description_index = max(vote_counts, key=vote_counts.get, default=None)

    return preferred_description_index
    

def add_indices_to_advice(advice_list):
    """
    Add indices to advice. Advice items will not change, so this is safe.
    """
    
    index = 1
    for item in advice_list:
        item['index'] = index
        index += 1

def get_all_cm_requests(project_dir, status='any'):
    params = { 'project_dir': project_dir }
    pages = get_pages(params)
    requests = []

    for page in pages:
        requests.extend(get_all_cm_requests_for_page(project_dir, page, status=status))

    return requests

def get_all_cm_requests_for_page(project_dir, page, status='any'):
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

    if status != 'any':
        requests = [ request for request in requests if request['status'] == status ]

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

def remove_cm_request(project_dir, request_item):
    """
    Remove a request
    """

    request_type = request_item['request_type']
    page_number = request_item['page']

    data = load_community_feedback(project_dir, page_number)

    if request_type == 'variants_requests':
        description_index = request_item['description_index']
        data['variants_requests'] = [ item for item in data['variants_requests']
                                      if item['description_index'] != description_index ]
    elif request_type == 'advice':
        index = request_item['index']
        data['advice'] = [ item for item in data['advice']
                           if item['index'] != index ]

    save_community_feedback(project_dir, page_number, data)
