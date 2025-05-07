#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.python-dotenv

import requests
import json # Added for JSON handling
from datetime import datetime # Added for date-based filenames
import re # Added for parsing Gemini's selection
import random # Added for random selection
import os # For checking file existence and getting env vars
from dotenv import load_dotenv # For loading .env file

# Load environment variables from .env file
load_dotenv()

# Your API key for Marginalia - loaded from .env
API_KEY = os.getenv("MARGINALIA_API_KEY")
BASE_URL = "https://api.marginalia.nu/{key}/search/{query}"

# Gemini API Configuration - loaded from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

PROMPTS_FILE = "prompts.json"
RECENT_INTERESTS_URL = "https://raw.githubusercontent.com/monksevillair/monksevillair.github.io/refs/heads/master/mc/recent_notes.txt"

# --- Sanity check for API keys ---
if not API_KEY:
    print("Error: MARGINALIA_API_KEY not found in .env file or environment variables.")
    print("Please ensure your .env file is correctly set up with MARGINALIA_API_KEY.")
    exit(1)

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
    print("Please ensure your .env file is correctly set up with GEMINI_API_KEY.")
    exit(1)
# Update the Gemini API URL with the potentially newly loaded key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

def load_all_prompts(filename=PROMPTS_FILE):
    """Loads immutable and mutable prompts from a JSON file."""
    default_prompts = {"immutable_prompts": [], "mutable_prompts": []}
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Ensure both keys exist and are lists of dicts with 'description'
            immutable = data.get("immutable_prompts", [])
            mutable = data.get("mutable_prompts", [])

            if not (isinstance(immutable, list) and all(isinstance(p, dict) and "description" in p for p in immutable)):
                print(f"Warning: 'immutable_prompts' in {filename} is not a list of valid prompt objects. Using empty list.")
                immutable = []
            if not (isinstance(mutable, list) and all(isinstance(p, dict) and "description" in p for p in mutable)):
                print(f"Warning: 'mutable_prompts' in {filename} is not a list of valid prompt objects. Using empty list.")
                mutable = []
            
            return {"immutable_prompts": immutable, "mutable_prompts": mutable}
    except FileNotFoundError:
        print(f"Info: Prompts file '{filename}' not found. Returning default structure.")
        return default_prompts
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filename}'. Returning default structure.")
        return default_prompts

def save_all_prompts(prompts_data, filename=PROMPTS_FILE):
    """Saves the prompts data (especially updated mutable_prompts) back to the JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(prompts_data, f, indent=2)
        print(f"Info: Successfully saved updated prompts to {filename}")
    except IOError:
        print(f"Error: Could not write prompts to file {filename}.")

def get_todays_json_filename():
    now = datetime.now()
    return f"{now.day}_{now.month}_{now.year}.json"

def load_todays_posts(filename):
    """Loads posts from today's JSON file."""
    posts = []
    try:
        with open(filename, 'r') as f:
            content = f.read()
            if content.strip(): # Check if file is not empty
                data = json.loads(content)
                if isinstance(data, list):
                    posts = data
                else:
                    print(f"Warning: Content in {filename} is not a list. Starting with an empty list of posts for context.")
            # If file is empty or only whitespace, posts remains []
    except FileNotFoundError:
        print(f"Info: Today's post file '{filename}' not found. Assuming no posts yet for context.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filename}'. Assuming no posts yet for context.")
    return posts

def fetch_recent_interests_from_url(url):
    """Fetches text content from a given URL."""
    print(f"Fetching recent interests from: {url}")
    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status()  # Will raise an HTTPError for bad status codes
        print("Successfully fetched recent interests.")
        return response.text.strip()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while fetching recent interests: {http_err} - Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred while fetching recent interests: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout occurred while fetching recent interests: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred while fetching recent interests: {req_err}")
    return None

def refine_mutable_prompt_with_gemini(current_mutable_prompt_desc, recent_interests_text):
    """Asks Gemini to refine a mutable prompt based on a list of recent interests from an external source."""
    if not current_mutable_prompt_desc:
        print("Info: No current mutable prompt description provided for refinement.")
        return None
    if not recent_interests_text: # Check if text was successfully fetched
        print("Info: No text describing recent interests was provided. Skipping mutable prompt refinement.")
        return current_mutable_prompt_desc

    print("\nAsking Gemini to refine the mutable interest prompt based on externally listed recent interests...")
    prompt = (
        "My overall long-term goals are defined by a separate, stable interest profile. "
        "This specific 'mutable interest profile' is designed to be dynamic and to closely reflect my *most current and explicit focus*, as directly stated in my recent notes. "
        f"Here is the current version of this mutable profile: \"{current_mutable_prompt_desc}\"\n\n"
        "The following text is a direct list/summary of topics I have noted as my *very recent interests* from an external source:\n"
        f"--- My Recently Noted Interests ---\n{recent_interests_text}\n--- End of Recent Interests ---\n\n"
        "Your task is to revise the mutable interest profile. The new version should:\n"
        "1. Strongly and clearly reflect the topics listed in 'My Recently Noted Interests'. These noted interests should take precedence and heavily influence the revised profile.\n"
        "2. Serve as a focused lens for discovering content related to these explicitly stated recent interests.\n"
        "3. While prioritizing the 'Recently Noted Interests', ensure the revised profile remains a coherent and useful statement for guiding search and content discovery.\n"
        "4. If the 'Recently Noted Interests' are significantly different from the current mutable profile, the revised profile should reflect this shift boldly. Don't be afraid to make substantial changes to align with this new, direct input.\n\n"
        "Please provide ONLY the revised mutable interest profile text. Do not include any other explanatory text, greetings, or markdown formatting."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 350, # Slightly more tokens if the prompt becomes more detailed
            "temperature": 0.75 # Increased temperature for more variability and change
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        gemini_data = response.json()
        candidates = gemini_data.get('candidates')
        if candidates and len(candidates) > 0:
            content = candidates[0].get('content')
            if content:
                parts = content.get('parts')
                if parts and len(parts) > 0:
                    refined_description = parts[0].get('text', '').strip()
                    if refined_description:
                        print(f"Gemini refined mutable prompt to: \"{refined_description}\"")
                        return refined_description
        print("Error: Could not extract refined prompt from Gemini response.")
        return current_mutable_prompt_desc # Fallback to original
    except Exception as e:
        print(f"Error during Gemini mutable prompt refinement: {e}")
        return current_mutable_prompt_desc # Fallback to original

def generate_search_query_with_gemini(interests_description, todays_posts_summary=""):
    """
    Generates a focused search query using the Gemini API based on user interests,
    aiming for variety based on today's existing posts.
    """
    print("Asking Gemini to generate a focused search query based on your interests and today's existing posts...")

    diversification_prompt_part = (
        "To ensure a varied and eclectic collection of discoveries for today, "
        "please generate a search query that explores a *different* aspect of my interests "
        "or a *new, complementary topic* to what has already been covered. "
        "Avoid significant repetition with the themes from today's existing posts."
    )
    if todays_posts_summary and todays_posts_summary != "No posts yet today.":
        diversification_prompt_part = (
            f"Here are summaries of posts already generated today:\n{todays_posts_summary}\n\n"
            "Considering these, to ensure a varied and eclectic collection of discoveries for today, "
            "please generate a search query that explores a *different* aspect of my interests "
            "or a *new, complementary topic*. Aim to find something that adds novelty or a new perspective "
            "relative to the posts already listed."
        )

    prompt = (
        f"My comprehensive interest profile is: {interests_description}\n\n"
        f"{diversification_prompt_part}\n\n"
        "I need a highly focused search query (ideally 2-4 words) for a niche, text-focused search engine like Marginalia, which surfaces unique and often technical or non-mainstream content. "
        "From my detailed interests above, and keeping in mind the goal of diversification, please identify a *specific sub-topic, a particular technology, a distinct problem, or a niche research area*. "
        "Then, formulate a concise search query that targets this *narrow aspect* directly. "
        "The goal is to find in-depth information or overlooked resources on that specific point, rather than a general overview of my broader interests or topics already covered today. "
        "For example, if my interests include 'underwater robotics and AI for coral reef monitoring', and today's posts are about 'AUV coral mapping', a good new query might be 'acoustic modem design for UUVs' or 'biofouling prevention on marine sensors', rather than another query about mapping or AI for reefs.\n"
        "Respond with ONLY the search query itself, without any extra explanation or quotation marks."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 20, # Short query expected
            "temperature": 0.7 # Allow for some creativity
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        gemini_data = response.json()

        candidates = gemini_data.get('candidates')
        if candidates and len(candidates) > 0:
            content = candidates[0].get('content')
            if content:
                parts = content.get('parts')
                if parts and len(parts) > 0:
                    generated_query = parts[0].get('text', '').strip()
                    if generated_query:
                        print(f"Gemini suggested search query: '{generated_query}'")
                        return generated_query
        
        print("Error: Could not extract search query from Gemini response.")
        # print(f"Gemini response for query generation: {gemini_data}") # For debugging
        return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Gemini API HTTP error during query generation: {http_err}")
        # print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the Gemini API request for query generation: {req_err}")
    except ValueError:
        print("Error: Could not decode JSON response from Gemini during query generation.")
        # print(f"Response content: {response.text}")
    return None

def search_marginalia(query):
    """
    Searches Marginalia using the provided query and API key.
    Returns the list of results.
    """
    # Construct the full API URL
    url = BASE_URL.format(key=API_KEY, query=query)

    print(f"Searching for: {query}...")
    print(f"Requesting URL: {url}\n")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        data = response.json()

        print("Query: ", data.get('query', 'N/A'))
        print("License: ", data.get('license', 'N/A'))
        results_list = data.get('results', [])
        print("Results found:", len(results_list))
        print("-" * 30)

        if results_list:
            for i, result in enumerate(results_list):
                print(f"\nResult {i+1}:")
                print(f"  URL: {result.get('url', 'N/A')}")
                print(f"  Title: {result.get('title', 'N/A')}")
                print(f"  Description: {result.get('description', 'N/A').strip()}")
        else:
            print("No results found.")
        
        return results_list # Return the list of results

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 503:
            print("This might be due to the API rate limit being hit for Marginalia.")
        # print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the Marginalia request: {req_err}")
    except ValueError: # Includes JSONDecodeError
        print("Error: Could not decode JSON response from Marginalia. The API might be down or returned unexpected data.")
        # print(f"Response content: {response.text}")
    return [] # Return empty list on error

def select_most_relevant_result_with_gemini(search_query, results_list, interests_description, todays_posts_summary=""):
    """
    Uses Gemini to select the most relevant search result, considering diversity based on today's posts
    and attempting to filter out AI spam.
    """
    if not results_list:
        print("No Marginalia results to select from.")
        return None
    if len(results_list) == 1:
        print("Only one Marginalia result found, selecting it by default.")
        return results_list[0]

    print(f"\nAsking Gemini to select the most relevant result for query '{search_query}' based on interests and today's context...")

    diversification_context = ""
    if todays_posts_summary and todays_posts_summary != "No posts yet today.":
        diversification_context = (
            f"For context, here are summaries of topics already posted today:\n{todays_posts_summary}\n\n"
            "When selecting, please favor a result that might offer a new angle or complementary information "
            "to ensure a diverse set of findings for the day.\n"
        )

    prompt_parts = [
        f"My primary interests are: {interests_description}\n\n",
        f"I performed a search for: '{search_query}'.\n",
        diversification_context,
        "Here are the top search results from Marginalia:\n\n"
    ]

    for i, result in enumerate(results_list):
        prompt_parts.append(f"Result {i+1}:\n")
        prompt_parts.append(f"  Title: {result.get('title', 'N/A')}\n")
        prompt_parts.append(f"  Description: {result.get('description', 'N/A')}\n")
        prompt_parts.append(f"  URL: {result.get('url', 'N/A')}\n\n")

    prompt_parts.append(
        "Considering my interests, the search query, and the goal of building a varied collection of posts (avoiding too much overlap with existing topics if possible), "
        "which of these results (e.g., 'Result 1', 'Result 2', etc.) "
        "is the most relevant AND interesting? Please respond with only the identifier (e.g., 'Result X'). "
        "If none seem particularly relevant or if they are too similar to existing posts, respond with 'None'.\n"
        "Additionally, try to discern and deprioritize results that seem like low-quality, generic, or AI-generated spam/content farms. Favor unique, insightful, or human-authored content."
    )
    prompt = "".join(prompt_parts)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": { # Added to guide Gemini for a short, specific answer
            "maxOutputTokens": 50,
            "temperature": 0.2
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        gemini_data = response.json()

        candidates = gemini_data.get('candidates')
        if candidates and len(candidates) > 0:
            content = candidates[0].get('content')
            if content:
                parts = content.get('parts')
                if parts and len(parts) > 0:
                    selection_text = parts[0].get('text', '').strip()
                    print(f"Gemini's selection advice: '{selection_text}'")

                    if selection_text.lower() == 'none':
                        print("Gemini indicated no result is particularly relevant.")
                        return None

                    # Try to parse "Result X"
                    match = re.search(r'Result\s*(\d+)', selection_text, re.IGNORECASE)
                    if match:
                        selected_index = int(match.group(1)) - 1
                        if 0 <= selected_index < len(results_list):
                            print(f"Gemini selected Result {selected_index + 1}.")
                            return results_list[selected_index]
                        else:
                            print(f"Gemini's selection index {selected_index + 1} is out of bounds.")
                    else:
                        print("Could not parse Gemini's selection. Defaulting to the first result if available.")
                        # Fallback if parsing fails but there was some text
                        if results_list: return results_list[0]
                        return None
        
        print("Error: Could not extract selection from Gemini response.")
        # print(f"Gemini response for selection: {gemini_data}") # For debugging
        return results_list[0] if results_list else None

    except requests.exceptions.HTTPError as http_err:
        print(f"Gemini API HTTP error during selection: {http_err}")
        # print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the Gemini API request for selection: {req_err}")
    except ValueError:
        print("Error: Could not decode JSON response from Gemini during selection.")
        # print(f"Response content: {response.text}")
    
    print("Selection by Gemini failed. Defaulting to the first result if available.")
    return results_list[0] if results_list else None

def generate_title_with_gemini(search_query, marginalia_result, existing_titles_str=""):
    """
    Generates a post title using the Gemini API, aiming for distinctiveness, quirkiness,
    and a Hacker News-style from existing titles.
    """
    if not marginalia_result:
        return None

    title_context = "When crafting this new title, try to make it distinct and complementary, contributing to an overall eclectic and interesting set of posts for the day."
    if existing_titles_str and existing_titles_str != "No existing titles for today.":
        title_context = (
            f"Here are the titles of posts already generated today:\n{existing_titles_str}\n\n"
            "When crafting this new title, try to make it distinct and complementary to these existing titles, "
            "contributing to an overall eclectic and interesting set of posts for the day."
        )

    prompt = (
        f"Based on the search query '{search_query}' and the following search result from Marginalia:\n"
        f"URL: {marginalia_result.get('url', 'N/A')}\n"
        f"Title: {marginalia_result.get('title', 'N/A')}\n"
        f"Description: {marginalia_result.get('description', 'N/A')}\n\n"
        f"{title_context}\n\n"
        "Please generate a quirky, intriguing, and Hacker News-style title for a new blog post about this topic. "
        "The title should spark curiosity and hint at the core interesting aspect of the content, often with a slightly informal or clever angle. "
        "It should be suitable for a JSON data entry and must not contain any special formatting or quotation marks that would break JSON structure. "
        "Just the plain text of the title. Think of titles you'd see on HN that make you want to click!"
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 70, # Slightly more room for creative/quirky titles
            "temperature": 0.75     # Encourage more variability and "quirkiness"
        }
    }
    headers = {
        'Content-Type': 'application/json'
    }

    print(f"\nRequesting title from Gemini for query: {search_query}...")
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        gemini_data = response.json()
        
        # Safely access the generated text
        candidates = gemini_data.get('candidates')
        if candidates and len(candidates) > 0:
            content = candidates[0].get('content')
            if content:
                parts = content.get('parts')
                if parts and len(parts) > 0:
                    generated_title = parts[0].get('text')
                    if generated_title:
                        print(f"Gemini generated title: {generated_title.strip()}")
                        return generated_title.strip()
        
        print("Error: Could not extract title from Gemini response.")
        # print(f"Gemini response: {gemini_data}") # For debugging
        return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Gemini API HTTP error occurred: {http_err}")
        print(f"Status Code: {response.status_code}")
        # print(f"Response content: {response.text}") # For debugging
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the Gemini API request: {req_err}")
    except ValueError: # Includes JSONDecodeError
        print("Error: Could not decode JSON response from Gemini.")
        # print(f"Response content: {response.text}") # For debugging
    return None

def generate_hn_style_comment_with_gemini(search_query, selected_interest_description, marginalia_result, todays_posts_summary=""):
    """
    Generates a single Hacker News-style comment, considering context from other posts today.
    """
    if not marginalia_result:
        return None

    comment_context = "When writing this comment, consider how it can add a unique perspective or touch upon an angle, making the overall set of discussions more varied and interesting."
    if todays_posts_summary and todays_posts_summary != "No posts yet today.":
        comment_context = (
            f"For context, here are themes/titles from other posts made today:\n{todays_posts_summary}\n\n"
            "When writing this comment about the current article, consider how it can add a unique perspective or touch upon an angle "
            "that complements or contrasts with the themes from other posts today, making the overall set of discussions more varied and interesting."
        )

    prompt = (
        f"My guiding interest profile for this task is: \"{selected_interest_description.strip()}\"\n\n"
        f"The search query used was: \"{search_query}\"\n\n"
        f"The following article was selected from the search results:\n"
        f"Title: {marginalia_result.get('title', 'N/A')}\n"
        f"URL: {marginalia_result.get('url', 'N/A')}\n"
        f"Description: {marginalia_result.get('description', 'N/A')}\n\n"
        f"{comment_context}\n\n"
        "Please generate a single, insightful comment about THIS article, written in the style of a Hacker News (HN) commentator. "
        "The comment should briefly explain why THIS article is interesting or relevant, particularly considering my stated interests and the search query. "
        "It can offer a concise take, connect to broader ideas, or highlight a key takeaway. Aim for a tone that is informed, slightly informal, and engaging. "
        "Respond ONLY with a single JSON object containing one key: \"hn_comment\", where the value is the text of your comment (1-3 sentences).\n\n"
        "Ensure your entire response is a valid JSON object and nothing else."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json", # Request JSON output
            "maxOutputTokens": 250, # Max tokens for a concise HN-style comment
            "temperature": 0.6 # Allow for a bit more personality
        }
    }
    headers = {'Content-Type': 'application/json'}

    print(f"\nRequesting HN-style comment from Gemini for article: {marginalia_result.get('title', 'N/A')}...")
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        raw_response_text = ""
        try:
            gemini_data = response.json()
            if 'candidates' in gemini_data and gemini_data['candidates'] and \
               'content' in gemini_data['candidates'][0] and \
               'parts' in gemini_data['candidates'][0]['content'] and \
               gemini_data['candidates'][0]['content']['parts']:
                raw_response_text = gemini_data['candidates'][0]['content']['parts'][0].get('text', '')
            else:
                raw_response_text = response.text
        except json.JSONDecodeError:
             raw_response_text = response.text

        cleaned_json_text = re.sub(r'^```json\s*|\s*```$', '', raw_response_text.strip(), flags=re.MULTILINE)

        try:
            comment_data = json.loads(cleaned_json_text)
            hn_comment = comment_data.get("hn_comment")

            if hn_comment:
                print(f"Gemini HN-Style Comment: {hn_comment}")
                return hn_comment
            else:
                print("Error: 'hn_comment' key not found in Gemini's JSON response.")
                print(f"Gemini parsed JSON was: {comment_data}")
                return None
        except json.JSONDecodeError as json_err:
            print(f"Error: Could not decode JSON response from Gemini for HN comment: {json_err}")
            print(f"Gemini raw response text was: {raw_response_text}")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Gemini API HTTP error during HN comment generation: {http_err}")
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the Gemini API request for HN comment: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred during HN comment generation: {e}")
    
    return None

def add_post_to_daily_json(post_title, post_url, hn_comment_text=None):
    """
    Adds a new post to a JSON file named with today's date, including a single HN-style comment.
    Initializes heart to 0 (neutral). Stores the creation time.
    """
    now = datetime.now()
    filename = f"{now.day}_{now.month}_{now.year}.json"
    creation_time_str = now.strftime("%I:%M %p") # Format as HH:MM AM/PM e.g., 03:45 PM
    
    posts = []
    try:
        with open(filename, 'r') as f:
            content = f.read()
            if content.strip():
                posts = json.loads(content)
                if not isinstance(posts, list):
                    print(f"Error: Existing content in {filename} is not a list. Aborting post addition.")
                    return
            else:
                posts = []
    except FileNotFoundError:
        print(f"File {filename} not found. Creating a new one.")
        posts = []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filename}. File might be corrupted. Aborting post addition.")
        return

    new_post_id = 1
    if posts:
        new_post_id = max(p.get("id", 0) for p in posts) + 1

    post_comments = []
    if hn_comment_text:
        post_comments.append({
            "id": f"c_gemini_hn_{new_post_id}_1", # Unique comment ID
            "author": "GeminiHNBot", 
            "text": hn_comment_text,
            "time_ago": creation_time_str, # Use formatted creation time
            "heart": 0, # Initialize heart to 0 (neutral) for new comments
            "comments": [] 
        })

    new_post = {
        "id": new_post_id,
        "title": post_title,
        "url": post_url,
        "points": 0,
        "author": "AutoGeneratedBot",
        "time_ago": creation_time_str, # Use formatted creation time
        "heart": 0, # Initialize heart to 0 (neutral) for new posts
        "comments_count": len(post_comments),
        "comments": post_comments
    }

    posts.append(new_post)

    try:
        with open(filename, 'w') as f:
            json.dump(posts, f, indent=2)
        print(f"\nSuccessfully added post '{post_title}' with {len(post_comments)} HN-style comment(s) to {filename}")
    except IOError:
        print(f"Error: Could not write to file {filename}.")


if __name__ == "__main__":
    # Step -1: Load prompts and refine mutable prompt based on external recent interests file
    all_prompts_data = load_all_prompts()
    current_mutable_prompts_list = all_prompts_data.get("mutable_prompts", [])
    
    # Fetch recent interests from the specified URL
    recent_interests_text = fetch_recent_interests_from_url(RECENT_INTERESTS_URL)

    if recent_interests_text and current_mutable_prompts_list:
        # Refine the first mutable prompt if it exists and recent interests were fetched
        if current_mutable_prompts_list: 
            original_mutable_prompt_obj = current_mutable_prompts_list[0]
            original_mutable_desc = original_mutable_prompt_obj.get("description")
            
            if original_mutable_desc: 
                refined_desc = refine_mutable_prompt_with_gemini(original_mutable_desc, recent_interests_text)
                
                if refined_desc and refined_desc != original_mutable_desc:
                    all_prompts_data["mutable_prompts"][0]["description"] = refined_desc
                    save_all_prompts(all_prompts_data)
                    print("Info: Mutable prompt was updated using external recent interests and saved.")
                elif refined_desc == original_mutable_desc:
                    print("Info: Mutable prompt was not changed by Gemini or refinement failed to produce a new version based on external interests.")
                else: 
                    print("Info: Mutable prompt refinement based on external interests failed, original prompt will be used for this session if selected.")
            else:
                print("Warning: First mutable prompt has no description, cannot refine.")
        else:
            print("Info: No mutable prompts to refine.")
    elif not recent_interests_text:
        print("Info: Could not fetch recent interests from URL. Mutable prompt will not be refined based on external notes for this session.")

    # --- Load today's posts for context ---
    todays_json_filename = get_todays_json_filename()
    todays_posts_data = load_todays_posts(todays_json_filename)
    
    todays_posts_summary_str = "No posts yet today."
    if todays_posts_data:
        post_summaries = []
        for post in todays_posts_data:
            title = post.get('title', "N/A")
            # url_snippet = post.get('url', '')[:50] + "..." if post.get('url') else "N/A"
            # post_summaries.append(f"- Title: \"{title}\" (URL: {url_snippet})")
            post_summaries.append(f"- \"{title}\"") # Simpler summary with just titles
        if post_summaries:
            todays_posts_summary_str = "\n".join(post_summaries)

    existing_titles_list_str = "No existing titles for today."
    if todays_posts_data:
        titles = [f"- \"{post.get('title', 'N/A')}\"" for post in todays_posts_data if post.get('title')]
        if titles:
            existing_titles_list_str = "\n".join(titles)
    
    # --- Prompt Selection for current run: Combine immutable and mutable if available ---
    immutable_prompts = all_prompts_data.get("immutable_prompts", [])
    # Use the potentially updated mutable prompts for selection
    mutable_prompts = all_prompts_data.get("mutable_prompts", []) 
    
    selected_interest_description = None
    prompt_source_parts = []
    
    chosen_immutable_desc = None
    chosen_mutable_desc = None

    if immutable_prompts:
        selected_immutable_prompt_obj = random.choice(immutable_prompts)
        chosen_immutable_desc = selected_immutable_prompt_obj.get("description")
        prompt_source_parts.append(f"Immutable ({selected_immutable_prompt_obj.get('id', 'N/A')})")

    if mutable_prompts:
        selected_mutable_prompt_obj = random.choice(mutable_prompts)
        chosen_mutable_desc = selected_mutable_prompt_obj.get("description")
        prompt_source_parts.append(f"Mutable ({selected_mutable_prompt_obj.get('id', 'N/A')})")

    if chosen_immutable_desc and chosen_mutable_desc:
        selected_interest_description = (
            f"My core guiding principles and long-term interests are: \"{chosen_immutable_desc}\"\n\n"
            f"My current evolving focus, potentially influenced by recent discoveries and feedback, is: \"{chosen_mutable_desc}\""
        )
    elif chosen_immutable_desc:
        selected_interest_description = chosen_immutable_desc
    elif chosen_mutable_desc:
        selected_interest_description = chosen_mutable_desc
    else:
        print("Fatal Error: No prompts available (neither immutable nor mutable descriptions found). Exiting.")
        exit()
    
    prompt_source = " + ".join(prompt_source_parts) if prompt_source_parts else "No specific prompt source"

    print(f"\n--- Using Interest Profile from: {prompt_source} ---")
    print(f"{selected_interest_description.strip()}")
    print(f"--------------------------------------------------\n")

    # Step 0: Generate search query with Gemini based on the selected interest and today's posts
    search_query = generate_search_query_with_gemini(selected_interest_description, todays_posts_summary_str)

    if search_query:
        # Step 1: Search Marginalia
        marginalia_results = search_marginalia(search_query)

        if marginalia_results:
            # Step 2a: Select the most relevant result, considering today's posts for diversity
            selected_result = select_most_relevant_result_with_gemini(
                search_query, 
                marginalia_results, 
                selected_interest_description,
                todays_posts_summary_str
            )
            
            if selected_result:
                print(f"\nProceeding with selected result: {selected_result.get('title', 'N/A')}")
                # Step 2b: Generate title, considering existing titles
                generated_title = generate_title_with_gemini(
                    search_query, 
                    selected_result,
                    existing_titles_list_str
                )
                
                if generated_title:
                    # Step 2c: Generate HN-style comment, considering today's posts
                    hn_comment = generate_hn_style_comment_with_gemini(
                        search_query, 
                        selected_interest_description, 
                        selected_result,
                        todays_posts_summary_str
                    )
                    
                    post_url = selected_result.get('url', 'N/A')
                    add_post_to_daily_json(
                        generated_title, 
                        post_url, 
                        hn_comment_text=hn_comment
                    )
                else:
                    print("Could not generate a title using Gemini. Post not added to JSON.")
            else:
                print("No relevant result selected by Gemini (or selection failed). Post not added to JSON.")
        else:
            print(f"No results from Marginalia for the query '{search_query}'.")
    else:
        print("Could not generate a search query using Gemini. Exiting.") 
