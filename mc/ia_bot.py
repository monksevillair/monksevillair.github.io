#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.python-dotenv python3Packages.isodate

import requests
import json
from datetime import datetime
import os
import random
import re
from urllib.parse import quote_plus # For URL encoding queries
from dotenv import load_dotenv

# --- Constants and Configuration Loading ---
load_dotenv()

# --- Anthropic API Configuration ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_MODEL_SONNET = "claude-3-5-sonnet-20240620"
DEFAULT_CLAUDE_MODEL = CLAUDE_MODEL_SONNET

# --- Gemini API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Using gemini-1.5-flash-latest as it's fast and capable for these tasks
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash-latest"

# --- File Paths ---
PROMPTS_FILE = "prompts.json" # General prompts, if used
IA_INTERESTS_FILE = "ia_interests.json" # Internet Archive specific interests
RECENT_INTERESTS_URL = "https://raw.githubusercontent.com/monksevillair/monksevillair.github.io/master/mc/recent_notes.txt"

# --- Internet Archive Bot Operational Parameters ---
IA_BOT_PARAMETERS = {
    "search_media_types": ["texts", "audio", "movies", "data", "software", "web"], # Default media types
    "max_results_per_api_call": 25, # How many results to fetch from IA API per query
    "max_items_to_consider_for_ai_selection": 7, # How many top IA results to send to AI (Claude or Gemini)
    "max_total_posts_per_run": 1, # Max posts to generate in one script execution
    "sort_options": [ # Field and direction
        {"field": "publicdate", "direction": "desc"},
        {"field": "downloads", "direction": "desc"},
        {"field": "avg_rating", "direction": "desc"},
        {"field": "week", "direction": "desc"} # Popularity this week
    ],
    "claude_query_generation": { # This will be replaced by gemini_query_generation
        "num_queries_to_generate": 3,
        "max_tokens": 600 
    },
    "gemini_query_generation": { # NEW for Gemini
        "num_queries_to_generate": 3, # Generate a few options
        "max_output_tokens": 600 # Ample space for query list and JSON structure
    },
    "claude_item_selection": { # This will be replaced by gemini_item_selection
        "max_tokens": 350
    },
    "gemini_item_selection": { # NEW for Gemini
        "max_output_tokens": 100 # For selecting an item index (JSON)
    },
    "claude_post_content_generation": {
        "max_tokens": 500 # For title and HN comment
    },
    "claude_prompt_mutation": {
        "max_tokens": 450 # For new prompt description
    }
}

# --- Sanity Checks ---
if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY not found in .env file.")
    exit(1)
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
    print("Please ensure your .env file is correctly set up with GEMINI_API_KEY.")
    exit(1)

# --- Utility Functions ---
def get_todays_json_filename():
    now = datetime.now()
    return f"{now.day}_{now.month}_{now.year}.json"

def load_todays_posts(filename):
    posts = []
    try:
        with open(filename, 'r') as f:
            content = f.read()
            if content.strip():
                data = json.loads(content)
                if isinstance(data, list): posts = data
                else: print(f"Warning: Content in {filename} is not a list.")
    except FileNotFoundError: pass # It's okay if the file doesn't exist yet
    except json.JSONDecodeError: print(f"Error: Could not decode JSON from '{filename}'.")
    return posts

def load_json_file(filename, error_message_prefix=""):
    try:
        with open(filename, 'r') as f: return json.load(f)
    except FileNotFoundError:
        print(f"Info: {error_message_prefix} file '{filename}' not found. Returning None.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {error_message_prefix} file '{filename}'. Returning None.")
    return None

def save_json_file(data, filename, success_message_prefix=""):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        if success_message_prefix:
            print(f"Info: {success_message_prefix} saved to '{filename}'.")
        return True
    except IOError as e: print(f"Error: Could not write to {filename}. {e}")
    except TypeError as e: print(f"Error: Could not serialize data to JSON for {filename}. {e}")
    return False

def fetch_text_from_url(url):
    if not url: return None
    print(f"Fetching text content from: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        print("Successfully fetched text content.")
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    return None

# --- Claude API Helper Functions ---
def call_claude_api(system_prompt, user_prompt, max_tokens, model=DEFAULT_CLAUDE_MODEL):
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    if system_prompt:
        payload["system"] = system_prompt

    print(f"\nCalling Claude API ({model}) with max_tokens: {max_tokens}...")
    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=120) # Increased timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"Claude API HTTP error: {http_err}")
        try: print(f"Response content: {response.text}")
        except: pass
    except requests.exceptions.RequestException as req_err:
        print(f"Claude API Request error: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred calling Claude API: {e}")
    return None

def extract_json_from_claude_response(claude_text_response):
    if not claude_text_response: return None
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', claude_text_response, re.DOTALL)
    json_str_to_parse = claude_text_response.strip()
    if match:
        json_str_to_parse = match.group(1).strip()
    
    try:
        return json.loads(json_str_to_parse)
    except json.JSONDecodeError:
        # Attempt to find the first '{' or '[' and parse from there
        first_char_index = -1
        for i, char in enumerate(json_str_to_parse):
            if char in ['{', '[']:
                first_char_index = i
                break
        if first_char_index != -1:
            try:
                return json.loads(json_str_to_parse[first_char_index:])
            except json.JSONDecodeError as e:
                print(f"Error: Could not extract valid JSON from Claude's response even with heuristics: {e}. Response snippet: {json_str_to_parse[:300]}...")
        else:
            print(f"Error: No JSON structure ({{...}} or [...]) found in Claude's response: {json_str_to_parse[:300]}...")
    return None

# --- Gemini API Helper Functions ---
def call_gemini_api(prompt_text, model_name=DEFAULT_GEMINI_MODEL, max_output_tokens=500, temperature=0.7, top_p=1.0, top_k=40, expect_json=False):
    """
    Calls the Gemini API.
    If expect_json is True, it will request JSON output and attempt to parse it directly.
    """
    gemini_api_url = f"{GEMINI_API_URL_BASE}/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    generation_config = {
        "temperature": temperature,
        "topP": top_p,
        "topK": top_k,
        "maxOutputTokens": max_output_tokens,
    }
    if expect_json:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": generation_config
    }
    headers = {'Content-Type': 'application/json'}

    print(f"\nCalling Gemini API ({model_name}) with max_output_tokens: {max_output_tokens}...")
    # print(f"Gemini Prompt (first 200 chars): {prompt_text[:200]}...") # For debugging

    try:
        response = requests.post(gemini_api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        gemini_data = response.json()

        if 'candidates' in gemini_data and gemini_data['candidates']:
            content = gemini_data['candidates'][0].get('content')
            if content and 'parts' in content and content['parts']:
                text_response = content['parts'][0].get('text')
                if text_response:
                    if expect_json:
                        try:
                            return json.loads(text_response)
                        except json.JSONDecodeError as e:
                            print(f"Error: Gemini was expected to return JSON, but failed to parse: {e}")
                            print(f"Gemini raw text response: {text_response[:500]}")
                            return None # Or handle error differently
                    return text_response # Return raw text if not expecting JSON
        
        print("Error: Could not extract valid text response from Gemini.")
        # print(f"Full Gemini response for debugging: {gemini_data}")
        return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Gemini API HTTP error: {http_err}")
        if response is not None:
            print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Gemini API Request error: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred calling Gemini API: {e}")
    return None

def extract_json_from_gemini_text_response(gemini_text_response):
    """
    Attempts to extract a JSON object from Gemini's text response if it wasn't directly returned as JSON.
    This is a fallback if expect_json=False was used or if Gemini wraps JSON in markdown.
    """
    if not gemini_text_response:
        return None

    # Standard backtick ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', gemini_text_response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Warning: Found content in backticks from Gemini, but failed to parse as JSON: {json_str[:200]}...")
            # Fall through to try parsing the whole string

    # Try parsing the whole string if no backticks or if backtick content failed
    try:
        return json.loads(gemini_text_response.strip())
    except json.JSONDecodeError:
        # Heuristic: find first '{' or '['
        start_brace = gemini_text_response.find('{')
        start_bracket = gemini_text_response.find('[')
        start_index = -1

        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start_index = start_brace
        elif start_bracket != -1:
            start_index = start_bracket
        
        if start_index != -1:
            try:
                data = json.loads(gemini_text_response[start_index:])
                print("Warning: Had to heuristically extract JSON from Gemini's text response.")
                return data
            except json.JSONDecodeError:
                print(f"Error: Could not extract valid JSON from Gemini's text response even with heuristics: {gemini_text_response[:300]}...")
        else:
            print(f"Error: No JSON structure found in Gemini's text response: {gemini_text_response[:300]}...")
    return None

# --- Internet Archive API Function ---
def search_internet_archive(query_terms, media_types=None, num_results=10, sort_by=None):
    """
    Searches the Internet Archive.
    query_terms: string of keywords.
    media_types: list of strings like ["texts", "audio"].
    num_results: int.
    sort_by: dict like {"field": "publicdate", "direction": "desc"}.
    """
    base_url = "https://archive.org/advancedsearch.php"
    
    # Fields to retrieve
    fields = [
        "identifier", "title", "description", "mediatype", "creator", "date", "publicdate",
        "avg_rating", "num_reviews", "downloads", "item_size", "subject"
    ]
    fl_params = "&".join([f"fl[]={f}" for f in fields])

    # Construct query
    # Basic query for terms (searches many fields by default)
    # We'll let users be specific in their query_terms if they want (e.g., "title:(X) AND creator:(Y)")
    # For simplicity here, we just pass query_terms directly.
    # More advanced: `(title:({query_terms}) OR description:({query_terms}) OR subject:({query_terms}))`
    # For now, just use the raw query_terms.
    
    q_parts = [query_terms]
    if media_types and isinstance(media_types, list) and len(media_types) > 0:
        mediatype_query = " OR ".join([f'mediatype:"{mt}"' for mt in media_types])
        q_parts.append(f"({mediatype_query})")
    
    full_query = " AND ".join(q_parts)
    
    params = {
        "q": full_query,
        "output": "json",
        "rows": num_results
    }
    if sort_by and "field" in sort_by and "direction" in sort_by:
        params["sort[]"] = f"{sort_by['field']} {sort_by['direction']}"

    print(f"Searching Internet Archive with query: {full_query}")
    print(f"Request URL (approx): {base_url}?q={quote_plus(full_query)}&{fl_params}&rows={num_results}&output=json" + (f"&sort[]={params['sort[]']}" if "sort[]" in params else ""))

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("response", {}).get("docs", [])
        print(f"Found {len(results)} items from Internet Archive.")
        # Add a direct URL to each item
        for item in results:
            item["item_url"] = f"https://archive.org/details/{item.get('identifier')}"
        return results
    except requests.exceptions.RequestException as e:
        print(f"Error during Internet Archive request: {e}")
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from Internet Archive.")
    return []

# --- Claude Interaction Functions for Internet Archive ---

def mutate_ia_prompt_with_claude(current_mutable_desc, recent_notes_text, core_interest_desc, max_tokens):
    system_prompt = (
        "You are an AI assistant specializing in refining a user's interest profiles for exploring the Internet Archive. "
        "Your task is to synthesize a new, concise 'evolving focus' description. "
        "This new description should integrate key themes from the user's 'recent notes/thoughts', "
        "while remaining aligned with their 'core Internet Archive interest' and the 'current evolving focus for IA'. "
        "The output should be a single paragraph. "
        "Your entire response MUST BE a single JSON object with one key: \"mutated_prompt_description\", "
        "where the value is the new description text. Do not include any other explanatory text."
    )
    user_prompt = (
        f"User's information for Internet Archive exploration:\n\n"
        f"1. Core Internet Archive Interest (long-term goals for IA):\n\"\"\"\n{core_interest_desc}\n\"\"\"\n\n"
        f"2. Current Evolving Focus for IA (the prompt part to be updated):\n\"\"\"\n{current_mutable_desc}\n\"\"\"\n\n"
        f"3. Recent Notes/Thoughts (new inputs to incorporate):\n\"\"\"\n{recent_notes_text}\n\"\"\"\n\n"
        "Synthesize these into an updated 'evolving focus' description for Internet Archive. "
        "It should reflect a natural evolution, informed by recent notes, and consistent with the core IA interest. "
        "Focus on clarity, conciseness, and capturing the essence of the evolution for finding unique IA content. "
        "Remember, provide ONLY the JSON: {\"mutated_prompt_description\": \"new_description_text\"}."
    )
    print("\nCalling Claude API to mutate Internet Archive interest prompt...")
    response_data = call_claude_api(system_prompt, user_prompt, max_tokens)

    if response_data and response_data.get('content') and response_data['content'][0].get('type') == 'text':
        claude_text = response_data['content'][0]['text']
        parsed_json = extract_json_from_claude_response(claude_text)
        if parsed_json and isinstance(parsed_json, dict):
            new_description = parsed_json.get("mutated_prompt_description")
            if new_description and isinstance(new_description, str):
                print(f"Claude successfully mutated IA prompt description:\n{new_description}")
                return new_description.strip()
            else: print(f"Error: 'mutated_prompt_description' key not found or invalid in Claude's JSON. Parsed: {parsed_json}")
        else: print(f"Error: Could not parse valid JSON dict from Claude for IA prompt mutation. Raw: {claude_text[:500]}")
    else: print(f"Error: Invalid/empty response from Claude for IA prompt mutation. Response: {response_data}")
    return None


def generate_ia_queries_with_gemini(interest_profile_description, num_queries, max_output_tokens, media_types_focus=None, existing_posts_context=""):
    """
    Generates Internet Archive search queries using Gemini.
    Aims to get a JSON list of queries directly from Gemini.
    """
    media_focus_prompt_part = ""
    if media_types_focus and isinstance(media_types_focus, list):
        media_focus_prompt_part = f"Consider focusing some queries on these media types if appropriate for the interests: {', '.join(media_types_focus)}.\n"

    context_for_diversity_part = ""
    if existing_posts_context and existing_posts_context not in ["No posts yet today.", "No existing titles for today."]:
        context_for_diversity_part = (
            "To ensure variety, I have already explored items related to these themes/titles today:\n"
            f"{existing_posts_context}\n"
            "Please provide queries that explore *different facets* or *new angles* of my interests relative to these.\n"
        )

    prompt = (
        f"You are an expert research strategist for the Internet Archive (archive.org). "
        "Your goal is to generate effective search query strings based on the user's interests, "
        "aiming to uncover unique, historically significant, or culturally valuable items like texts, audio, video, datasets, or old software. "
        "Queries should be suitable for Internet Archive's search. They can be general terms or use field specifiers like 'title:(...)', 'subject:(...)', 'creator:(...)' when highly relevant to a core aspect of the interest. "
        "Strive for a balance: while unique finds are great, queries should also be broad enough to likely yield some results for exploration. A mix of somewhat specific and more general thematic queries is ideal.\n\n"
        f"User's interest profile for Internet Archive exploration is:\n{interest_profile_description}\n\n"
        f"{media_focus_prompt_part}"
        f"{context_for_diversity_part}"
        f"Based on this, please generate exactly {num_queries} diverse and effective search query strings for Internet Archive. "
        "Aim for queries that might uncover interesting content, but avoid making them so narrow (e.g., by combining too many very specific terms or obscure field specifiers) that they are unlikely to return any results. "
        "Focus on the core themes and concepts in the user's interests.\n\n"
        "Respond with ONLY a single JSON object with one key: \"IA_queries\", where the value is a list of the requested query strings. "
        "Example: {\"IA_queries\": [\"rare maps 17th century\", \"subject:(oral histories) AND collection:(folkways)\", \"early computing manuals\", \"underwater exploration documentaries\"]}"
    )

    # Request JSON directly from Gemini
    # Consider slightly increasing temperature for more varied (potentially broader) queries
    parsed_json = call_gemini_api(prompt, max_output_tokens=max_output_tokens, expect_json=True, temperature=0.75)

    if parsed_json and isinstance(parsed_json, dict):
        queries = parsed_json.get("IA_queries")
        if queries and isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            print(f"Gemini generated Internet Archive queries: {queries}")
            return queries
        else:
            print(f"Error: 'IA_queries' key not found or invalid format in Gemini's JSON response. Parsed: {parsed_json}")
    elif isinstance(parsed_json, str): # Fallback if expect_json failed and returned text
        print("Warning: Gemini did not return direct JSON, attempting to parse text response.")
        json_from_text = extract_json_from_gemini_text_response(parsed_json)
        if json_from_text and isinstance(json_from_text, dict):
            queries = json_from_text.get("IA_queries")
            if queries and isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                print(f"Gemini generated Internet Archive queries (from text fallback): {queries}")
                return queries
            else:
                print(f"Error: 'IA_queries' key not found or invalid format in Gemini's fallback parsed JSON. Parsed: {json_from_text}")
    else:
        print(f"Error: Could not get valid JSON response from Gemini for IA queries. Response: {parsed_json}")
    
    return []


def select_most_relevant_ia_item_with_gemini(search_query, ia_results, interest_profile, max_output_tokens, existing_posts_context=""):
    """
    Uses Gemini to select the most relevant Internet Archive item.
    Expects Gemini to return a JSON object with the selected index.
    """
    if not ia_results: return None
    if len(ia_results) == 1:
        print("Only one IA result, selecting it by default.")
        return ia_results[0]

    context_for_diversity_part = ""
    if existing_posts_context and existing_posts_context not in ["No posts yet today.", "No existing titles for today."]:
        context_for_diversity_part = (
            "For context, here are themes/titles from items already posted today:\n"
            f"{existing_posts_context}\n\n"
            "When selecting, please favor an item that offers a new angle or complementary information if possible.\n"
        )

    prompt_parts = [
        "You are an expert curator for the Internet Archive. Your task is to select the single most relevant, interesting, "
        "and high-quality item from a list of search results, based on the user's interests and the original search query. "
        "Consider factors like uniqueness, historical significance, completeness, and relevance to the user's stated goals. "
        "If multiple items are good, prioritize novelty or diversity compared to what might have been seen before.\n\n",
        f"User's primary interests for Internet Archive are: {interest_profile}\n\n",
        f"The search on Internet Archive was for: '{search_query}'.\n",
        context_for_diversity_part,
        "Here are the top search results:\n\n"
    ]

    for i, item in enumerate(ia_results):
        title = item.get('title', 'N/A')
        desc_snippet = (item.get('description', 'N/A') or "No description")[:250]
        creator = item.get('creator', 'N/A')
        mediatype = item.get('mediatype', 'N/A')
        pub_date = item.get('publicdate', item.get('date', 'N/A'))
        item_url = item.get('item_url', 'N/A')

        prompt_parts.append(f"Item {i+1}:\n")
        prompt_parts.append(f"  Title: {title}\n")
        prompt_parts.append(f"  Creator(s): {creator}\n")
        prompt_parts.append(f"  MediaType: {mediatype}\n")
        prompt_parts.append(f"  Published: {pub_date}\n")
        prompt_parts.append(f"  Description Snippet: {desc_snippet}...\n")
        prompt_parts.append(f"  URL: {item_url}\n\n")

    prompt_parts.append(
        "Considering my interests, the search query, and the goal of finding truly valuable or unique items (and diversifying from today's finds), "
        "which of these items (Item 1, Item 2, etc.) is the single best choice? \n"
        "Respond with ONLY a single JSON object with one key: \"selected_item_index\", "
        "where the value is the 1-based index of the selected item (e.g., 1, 2, 3,...). "
        "If no item is suitable or sufficiently interesting, the value should be 0 or null. "
        "Example for selecting item 2: {\"selected_item_index\": 2}. Example for no selection: {\"selected_item_index\": 0}"
    )
    prompt = "".join(prompt_parts)

    print(f"\nAsking Gemini to select the most relevant IA item for query '{search_query}'...")
    # Request JSON directly
    parsed_json = call_gemini_api(prompt, max_output_tokens=max_output_tokens, expect_json=True, temperature=0.3)


    if parsed_json and isinstance(parsed_json, dict):
        selected_index_val = parsed_json.get("selected_item_index")
        if selected_index_val is not None: # Allows 0
            try:
                selected_index = int(selected_index_val) - 1 # Convert to 0-based
                if selected_index == -1: # Corresponds to 0 from Gemini, meaning no selection
                    print("Gemini indicated no item is suitable.")
                    return None
                if 0 <= selected_index < len(ia_results):
                    print(f"Gemini selected Item {selected_index + 1}.")
                    return ia_results[selected_index]
                else:
                    print(f"Gemini's selection index {selected_index_val} is out of bounds for {len(ia_results)} items.")
            except ValueError:
                print(f"Gemini's selection '{selected_index_val}' is not a valid number.")
        else:
            print(f"Error: 'selected_item_index' key not found in Gemini's JSON response for selection. Parsed: {parsed_json}")
    elif isinstance(parsed_json, str): # Fallback if expect_json failed
        print("Warning: Gemini did not return direct JSON for selection, attempting to parse text response.")
        # This part would need a more robust text parsing if Gemini doesn't adhere to JSON output strictly
        # For now, we assume if it's text, it's an error or unexpected format.
        print(f"Gemini text response (fallback): {parsed_json[:500]}")
    else:
        print(f"Error: Could not get valid JSON response from Gemini for IA item selection. Response: {parsed_json}")
    
    print("Selection by Gemini failed or no item chosen. Defaulting to first result if available.")
    return ia_results[0] if ia_results else None


def generate_post_content_for_ia_item_with_claude(interest_profile_desc, ia_item, search_query, max_tokens, existing_posts_context=""):
    if not ia_item: return None, None
    
    item_title = ia_item.get('title', 'N/A')
    item_creator = ia_item.get('creator', 'N/A')
    item_mediatype = ia_item.get('mediatype', 'N/A')
    item_description_snippet = (ia_item.get('description', 'N/A') or "No description")[:500]
    item_url = ia_item.get('item_url', f"https://archive.org/details/{ia_item.get('identifier', 'N/A')}")

    system_prompt = (
        "You are a creative assistant and insightful commentator, specializing in crafting content in the style of Hacker News (HN) about items from the Internet Archive.\n"
        "Your task is to generate:\n"
        "1. A Hacker News-style title for a blog post about the provided Internet Archive item. The title should closely reflect the original item's content or title, while being concise, intriguing, and factual, suitable for HN. It should highlight a core discovery, historical context, or unique aspect. Avoid hype.\n"
        "2. A concise (1-3 sentences) Hacker News-style comment about the item, explaining its relevance, interesting technical/historical aspects, or unique value, based on the user's interests and the item's nature.\n\n"
        "Your entire response MUST BE a single JSON object with two keys:\n"
        "- \"title\": A string value for the generated title (JSON-safe plain text).\n"
        "- \"hn_comment\": A string value for the generated comment.\n\n"
        "Do not include any other explanatory text, greetings, or markdown formatting outside the JSON object itself."
    )

    context_info = "When crafting the title and comment, try to make them distinct and complementary if there are existing posts today."
    if existing_posts_context and existing_posts_context not in ["No posts yet today.", "No existing titles for today."]:
        context_info = (
            f"Context about posts already made today (titles/themes):\n{existing_posts_context}\n\n"
            "Craft the new title and comment to be distinct and complementary, adding to an eclectic set of content."
        )
    
    interest_prompt_part = f"My guiding interest profile for Internet Archive is: \"{interest_profile_desc.strip()}\"\n\n" if interest_profile_desc else ""

    user_prompt = (
        f"{interest_prompt_part}"
        f"The Internet Archive item details are:\n"
        f"Original Title: {item_title}\n"
        f"Creator(s): {item_creator}\n"
        f"MediaType: {item_mediatype}\n"
        f"Description Snippet: {item_description_snippet}...\n"
        f"URL: {item_url}\n"
        f"Original Search Query: '{search_query}'\n\n"
        f"{context_info}\n\n"
        "Please generate the title and comment as per the required JSON format. "
        "The title should be HN-style: concise, intriguing, factual, and closely based on the item's original title or primary subject matter. "
        "The comment should explain why THIS item is interesting/valuable, especially considering my stated interests and the nature of Internet Archive content (e.g., historical value, rarity, specific insights). "
        "Remember, your entire response must be ONLY the JSON object: {\"title\": \"your title\", \"hn_comment\": \"your comment\"}."
    )

    print(f"\nRequesting post content (title & comment) from Claude for IA item: {item_title}...")
    response_data = call_claude_api(system_prompt, user_prompt, max_tokens)

    if response_data and response_data.get('content') and response_data['content'][0].get('type') == 'text':
        claude_text = response_data['content'][0]['text']
        parsed_json = extract_json_from_claude_response(claude_text)

        if parsed_json and isinstance(parsed_json, dict):
            generated_title = parsed_json.get("title")
            hn_comment = parsed_json.get("hn_comment")

            if generated_title and isinstance(generated_title, str) and hn_comment and isinstance(hn_comment, str):
                generated_title = re.sub(r'^["\']|["\']$', '', generated_title.strip())
                if not generated_title:
                    print(f"Error: Claude returned an empty title in JSON. Raw: {claude_text}")
                    return None, None
                print(f"Claude generated title: {generated_title}")
                print(f"Claude generated HN-Style Comment: {hn_comment}")
                return generated_title.strip(), hn_comment.strip()
            else:
                missing = [k for k in ["title", "hn_comment"] if not parsed_json.get(k) or not isinstance(parsed_json.get(k), str)]
                print(f"Error: Missing/invalid keys ({', '.join(missing)}) in Claude's JSON for IA post content. Parsed: {parsed_json}")
        else: print(f"Error: Could not parse valid JSON dict from Claude for IA post content. Raw: {claude_text[:500]}")
    else: print(f"Error: Invalid/empty response from Claude for IA post content. Response: {response_data}")
    return None, None

# --- Main Application Logic ---
def add_post_to_daily_json(post_title, item_url, hn_comment_text=None, source_bot="ArchiveBot_MixedAI", item_mediatype="unknown"):
    now = datetime.now()
    filename = get_todays_json_filename()
    creation_time_str = now.strftime("%I:%M %p")
    posts = load_todays_posts(filename) # load_todays_posts handles FileNotFoundError by returning []
    
    new_post_id = max((p.get("id", 0) for p in posts if isinstance(p, dict)), default=0) + 1
    
    post_comments = []
    if hn_comment_text:
        post_comments.append({
            "id": f"c_claude_ia_{new_post_id}_1", "author": "ClaudeArchiveCommenter",
            "text": hn_comment_text, "time_ago": creation_time_str, "heart": 0, "comments": []
        })
    new_post = {
        "id": new_post_id, "title": post_title, "url": item_url, "points": 0,
        "author": source_bot, "time_ago": creation_time_str, "heart": 0,
        "comments_count": len(post_comments), "comments": post_comments,
        "source_type": item_mediatype # Store the mediatype from IA
    }
    posts.append(new_post)
    try:
        with open(filename, 'w') as f: json.dump(posts, f, indent=2)
        print(f"\nAdded Internet Archive post '{post_title}' (Type: {item_mediatype}) to {filename}")
    except IOError: print(f"Error writing to {filename}.")

def is_item_already_posted(item_url, todays_posts):
    return any(isinstance(p, dict) and p.get('url') == item_url for p in todays_posts)

if __name__ == "__main__":
    print("--- Internet Archive Content Bot (Mixed AI) Starting ---")

    ia_interests_data = load_json_file(IA_INTERESTS_FILE, "Internet Archive interests")
    if not ia_interests_data:
        print(f"Exiting: Missing or invalid {IA_INTERESTS_FILE}.")
        exit(1)
    
    # --- Optional: Mutate the mutable IA prompt ---
    recent_notes = fetch_text_from_url(RECENT_INTERESTS_URL)
    core_ia_interest_for_mutation = None
    if ia_interests_data.get("immutable_prompts"):
        # Use a random immutable prompt as context for mutation
        core_ia_interest_for_mutation = random.choice(ia_interests_data["immutable_prompts"])['description']

    if recent_notes and core_ia_interest_for_mutation and ia_interests_data.get("mutable_prompts"):
        mutable_ia_prompt_obj = ia_interests_data["mutable_prompts"][0] # Mutate the first one
        original_mutable_ia_desc = mutable_ia_prompt_obj.get("description")

        if original_mutable_ia_desc:
            mutation_config = IA_BOT_PARAMETERS.get("claude_prompt_mutation", {})
            mutation_max_tokens = mutation_config.get("max_tokens", 400)
            
            print(f"\nAttempting to mutate IA mutable prompt ID: {mutable_ia_prompt_obj.get('id', 'N/A')}")
            new_mutable_ia_desc = mutate_ia_prompt_with_claude(
                original_mutable_ia_desc, recent_notes, core_ia_interest_for_mutation, mutation_max_tokens
            )
            if new_mutable_ia_desc and new_mutable_ia_desc != original_mutable_ia_desc:
                ia_interests_data["mutable_prompts"][0]["description"] = new_mutable_ia_desc
                if save_json_file(ia_interests_data, IA_INTERESTS_FILE, "Updated Internet Archive interests"):
                    print("Successfully saved mutated IA prompt.")
                else:
                    print("Warning: Failed to save mutated IA prompt. Using it for this session only.")
            elif new_mutable_ia_desc == original_mutable_ia_desc:
                print("Info: Mutated IA prompt is identical to original. No changes.")
            else:
                print("Info: IA prompt mutation failed or returned no new description.")
        else: print("Info: No description in first mutable IA prompt to mutate.")
    # --- End of prompt mutation ---

    # Re-extract descriptions after potential mutation
    ia_immutable_descs = [p['description'] for p in ia_interests_data.get("immutable_prompts", []) if p.get('description')]
    ia_mutable_descs = [p['description'] for p in ia_interests_data.get("mutable_prompts", []) if p.get('description')]
    
    ia_interest_profile_parts = []
    chosen_immutable_desc = random.choice(ia_immutable_descs) if ia_immutable_descs else None
    chosen_mutable_desc = random.choice(ia_mutable_descs) if ia_mutable_descs else None

    if chosen_immutable_desc:
        ia_interest_profile_parts.append(f"Core IA Interests: \"{chosen_immutable_desc}\"")
    if chosen_mutable_desc:
        ia_interest_profile_parts.append(f"Evolving IA Focus: \"{chosen_mutable_desc}\"")

    if not ia_interest_profile_parts:
        print("Error: No IA interest descriptions found. Cannot generate queries.")
        exit(1)
    
    ia_interest_profile_full = "\n\n".join(ia_interest_profile_parts)
    print(f"\nUsing Internet Archive Interest Profile:\n{ia_interest_profile_full}\n" + "-"*30)

    todays_json_filename = get_todays_json_filename()
    todays_posts_data = load_todays_posts(todays_json_filename)
    
    todays_context_for_claude = "No posts yet today."
    if todays_posts_data:
        post_titles = [p.get('title', "N/A") for p in todays_posts_data if isinstance(p, dict) and p.get('title')]
        if post_titles:
            todays_context_for_claude = "\n".join([f"- \"{title}\"" for title in post_titles])
    
    # Get parameters
    bot_params = IA_BOT_PARAMETERS
    # Use Gemini specific config if available, else fallback or use a general one
    query_gen_config = bot_params.get("gemini_query_generation", bot_params["claude_query_generation"]) 
    item_select_config = bot_params.get("gemini_item_selection", bot_params["claude_item_selection"])
    content_gen_config = bot_params["claude_post_content_generation"]
    
    target_media_types = bot_params.get("search_media_types", ["texts"])
    sort_choice = random.choice(bot_params.get("sort_options", [{"field": "publicdate", "direction": "desc"}]))

    generated_ia_queries = generate_ia_queries_with_gemini(
        ia_interest_profile_full,
        query_gen_config["num_queries_to_generate"],
        query_gen_config.get("max_output_tokens", query_gen_config.get("max_tokens")), # Adapt to new key name
        media_types_focus=target_media_types,
        existing_posts_context=todays_context_for_claude
    )

    if not generated_ia_queries:
        print("No search queries generated by Gemini for Internet Archive. Exiting.")
        exit(1)

    posted_count_this_run = 0
    max_posts_this_run = bot_params["max_total_posts_per_run"]

    print("\n--- Processing Gemini-Generated Internet Archive Queries ---")
    for query_text in generated_ia_queries:
        if posted_count_this_run >= max_posts_this_run:
            print(f"Reached overall post limit ({max_posts_this_run}). Stopping.")
            break
        
        print(f"\nProcessing IA query: \"{query_text}\" (Sorting by {sort_choice['field']} {sort_choice['direction']})")
        # Use target_media_types for this specific search
        ia_search_results = search_internet_archive(
            query_text,
            media_types=target_media_types,
            num_results=bot_params["max_results_per_api_call"],
            sort_by=sort_choice
        )
        
        if not ia_search_results:
            print(f"No results from Internet Archive for query: '{query_text}'.")
            continue

        # Filter out already posted items before sending to Gemini for selection
        unposted_results = [
            item for item in ia_search_results 
            if not is_item_already_posted(item.get("item_url"), todays_posts_data)
        ]

        if not unposted_results:
            print(f"All results for query '{query_text}' seem to be already posted or no results. Skipping selection.")
            continue
            
        # Limit items sent to Gemini for selection
        items_for_ai_selection = unposted_results[:bot_params.get("max_items_to_consider_for_ai_selection", 7)]

        selected_ia_item = select_most_relevant_ia_item_with_gemini(
            query_text,
            items_for_ai_selection,
            ia_interest_profile_full,
            item_select_config.get("max_output_tokens", item_select_config.get("max_tokens")), # Adapt to new key name
            existing_posts_context=todays_context_for_claude
        )

        if selected_ia_item:
            item_url = selected_ia_item.get("item_url")
            if is_item_already_posted(item_url, todays_posts_data): # Final check, though unlikely if filtered above
                print(f"Selected IA item {item_url} already posted. Skipping.")
                continue

            generated_title, hn_comment = generate_post_content_for_ia_item_with_claude(
                ia_interest_profile_full,
                selected_ia_item,
                query_text, # Pass the original query for context
                content_gen_config["max_tokens"],
                existing_posts_context=todays_context_for_claude
            )

            if generated_title and hn_comment:
                item_mediatype = selected_ia_item.get("mediatype", "unknown")
                add_post_to_daily_json(generated_title, item_url, hn_comment, item_mediatype=item_mediatype)
                
                # Update context for subsequent operations in this run
                todays_posts_data.append({"url": item_url, "title": generated_title}) 
                current_titles = [p.get('title', "N/A") for p in todays_posts_data if isinstance(p,dict) and p.get('title')]
                if current_titles:
                    todays_context_for_claude = "\n".join([f"- \"{t}\"" for t in current_titles])
                
                posted_count_this_run += 1
            else:
                print(f"Could not generate title/comment for IA item from query '{query_text}'.")
        else:
            print(f"No suitable IA item selected by Gemini for query '{query_text}'.")

    print(f"\n--- Internet Archive Content Bot Finished. Posted {posted_count_this_run} new item(s). ---") 
