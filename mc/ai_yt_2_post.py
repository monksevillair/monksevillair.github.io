#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.requests python3Packages.python-dotenv python3Packages.google-api-python-client python3Packages.google-auth-httplib2 python3Packages.google-auth python3Packages.isodate

import requests
import json
from datetime import datetime, timezone, timedelta # timedelta might be used for published_after
import os
import random
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build # For YouTube
from googleapiclient.errors import HttpError as YouTubeHttpError # Alias to avoid conflict
import isodate # For parsing ISO 8601 durations

# --- Constants and Configuration Loading ---
load_dotenv()

# --- Gemini API Configuration (Kept for reference or if you mix models, but not used in Claude functions) ---
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"

# --- Anthropic API Configuration ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# Choose your preferred Claude model
# CLAUDE_MODEL_OPUS = "claude-3-opus-20240229"
CLAUDE_MODEL_SONNET = "claude-3-5-sonnet-20240620" # Latest Sonnet as of mid-2024
# CLAUDE_MODEL_HAIKU = "claude-3-haiku-20240307"
DEFAULT_CLAUDE_MODEL = CLAUDE_MODEL_SONNET

# --- YouTube API Configuration ---
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# --- File Paths ---
PROMPTS_FILE = "prompts.json"
YOUTUBE_INTERESTS_FILE = "youtube_interests.json"
RECENT_INTERESTS_URL = "https://raw.githubusercontent.com/monksevillair/monksevillair.github.io/master/mc/recent_notes.txt" # Raw content URL

# --- Hardcoded YouTube Bot Operational Parameters ---
YOUTUBE_BOT_PARAMETERS = {
  "video_duration_filter": {"min_seconds": 180, "max_seconds": 7200},
  "max_total_posts_per_run": 1, # MODIFIED: Ensure only one post per script execution
  "Youtube_defaults": {
    "max_results_per_fetch": 3,
    "post_limit_per_generated_query": 1, # Can also be 1, as max_total_posts_per_run is 1
    "order_by": "relevance"
  },
  "claude_query_generation": {
    "num_queries_to_generate": 4, # Generates a few options for the single post
    "max_tokens": 500
  },
  "claude_post_content_generation": { # MODIFIED: Combined title and comment generation
      "max_tokens": 450 # Sufficient for title (e.g., 100) + comment (e.g., 300) + JSON overhead
  },
  "claude_prompt_mutation": { # NEW: For mutating the mutable interest prompt
      "max_tokens": 400 # Max tokens for Claude to generate the new prompt description
  }
}

# --- Sanity Checks ---
if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY not found in .env file.")
    exit(1)
if not YOUTUBE_API_KEY:
    print("Error: YOUTUBE_API_KEY not found in .env file.")
    exit(1)
else:
    # ADDED: Print parts of the loaded YouTube API key for verification
    key_display = "None"
    if YOUTUBE_API_KEY:
        if len(YOUTUBE_API_KEY) > 8:
            key_display = f"{YOUTUBE_API_KEY[:4]}...{YOUTUBE_API_KEY[-4:]}"
        else: # For very short (likely invalid) keys, show what was loaded
            key_display = YOUTUBE_API_KEY
    print(f"Info: YOUTUBE_API_KEY loaded. Key preview: {key_display}")
    print("Info: If you see 'API key not valid' errors from YouTube, please ensure this key is correct in your .env file, active, and properly configured in the Google Cloud Console for the 'YouTube Data API v3' with necessary permissions and no restrictive quotas.")

# --- Utility Functions (largely unchanged) ---
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
            else: print(f"Info: Today's post file '{filename}' is empty.")
    except FileNotFoundError: print(f"Info: Today's post file '{filename}' not found.")
    except json.JSONDecodeError: print(f"Error: Could not decode JSON from '{filename}'.")
    return posts

def load_json_file(filename, error_message_prefix=""):
    try:
        with open(filename, 'r') as f: return json.load(f)
    except FileNotFoundError: print(f"Error: {error_message_prefix} file '{filename}' not found.")
    except json.JSONDecodeError: print(f"Error: Could not decode JSON from {error_message_prefix} file '{filename}'.")
    return None

load_general_prompts = lambda filename=PROMPTS_FILE: load_json_file(filename, "General prompts")
load_youtube_interests = lambda filename=YOUTUBE_INTERESTS_FILE: load_json_file(filename, "YouTube interests")

# --- YouTube API Functions (unchanged) ---
youtube_service = None
def get_youtube_service():
    global youtube_service
    if youtube_service is None:
        try:
            youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            print("YouTube service initialized successfully.")
        except Exception as e:
            print(f"Error initializing YouTube service: {e}")
            return None
    return youtube_service

def search_youtube_videos(query, max_results=5, order_by="date", published_after_iso=None):
    service = get_youtube_service()
    if not service: return []
    try:
        request_params = {"part": "snippet", "q": query, "type": "video", "order": order_by, "maxResults": max_results}
        if published_after_iso: request_params["publishedAfter"] = published_after_iso
        response = service.search().list(**request_params).execute()
        return response.get("items", [])
    except YouTubeHttpError as e: print(f"YouTube API HTTP error {e.resp.status}: {e.content}")
    except Exception as e: print(f"Error searching YouTube for '{query}': {e}")
    return []

def get_video_details(video_id):
    service = get_youtube_service()
    if not service: return None
    try:
        response = service.videos().list(part="snippet,contentDetails,statistics", id=video_id).execute()
        return response["items"][0] if response.get("items") else None
    except YouTubeHttpError as e: print(f"YouTube API HTTP error fetching details for {video_id}: {e.content}")
    except Exception as e: print(f"Error fetching details for video {video_id}: {e}")
    return None

# --- Claude API Helper Function ---
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
    # print(f"System Prompt: {system_prompt}") # For debugging
    # print(f"User Prompt: {user_prompt[:200]}...") # For debugging

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=90) # Increased timeout
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"Claude API HTTP error: {http_err}")
        try:
            print(f"Response content: {response.text}") # Print response if possible
        except:
            pass
    except requests.exceptions.RequestException as req_err:
        print(f"Claude API Request error: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred calling Claude API: {e}")
    return None

def extract_json_from_claude_response(claude_text_response):
    """
    Attempts to extract a JSON object or list from Claude's text response.
    Claude might sometimes wrap JSON in backticks or add conversational text.
    """
    if not claude_text_response:
        return None

    # Standard backtick ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', claude_text_response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Warning: Found content in backticks, but failed to parse as JSON: {json_str[:200]}...")
            # Fall through to try parsing the whole string if backtick content fails

    # Try parsing the whole string if no backticks or if backtick content failed
    try:
        return json.loads(claude_text_response.strip())
    except json.JSONDecodeError:
        # If it's not a perfect JSON string, look for the first '{' or '['
        # and try to parse from there to the corresponding '}' or ']'
        # This is a bit more heuristic.
        start_brace = claude_text_response.find('{')
        start_bracket = claude_text_response.find('[')

        start_index = -1
        is_object = False

        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start_index = start_brace
            is_object = True
        elif start_bracket != -1:
            start_index = start_bracket
            is_object = False # It's an array

        if start_index != -1:
            json_candidate_str = claude_text_response[start_index:]
            # Try to find matching brace/bracket (very simplified, might not handle nested structures perfectly if malformed)
            # This is a common source of errors if Claude's output isn't perfect JSON.
            # For robust parsing of imperfect JSON, more advanced techniques are needed.
            # Here, we'll just try to load it.
            try:
                # A more robust way to find the end of the JSON structure is hard if it's not well-formed.
                # We'll rely on json.loads to find the end of the first valid structure.
                data = json.loads(json_candidate_str)
                print("Warning: Had to heuristically extract JSON from Claude's response.")
                return data
            except json.JSONDecodeError:
                print(f"Error: Could not extract valid JSON from Claude's response even with heuristics: {claude_text_response[:300]}...")
        else:
            print(f"Error: No JSON structure ({{...}} or [...]) found in Claude's response: {claude_text_response[:300]}...")

    return None


# --- Claude Interaction Functions ---
def generate_Youtube_queries_with_claude(interest_profile_description, num_queries_to_generate, max_tokens, existing_queries_today=None):
    if existing_queries_today is None: existing_queries_today = []

    system_prompt = (
        "You are an expert Youtube strategist. Your goal is to generate effective search queries "
        "based on the user's interests, with a strong preference for uncovering content that is both **interesting and technical**, "
        "and comes from passionate, independent creators, hobbyists, and smaller channels offering unique perspectives. "
        "Please try to generate queries that avoid overly polished, corporate, or content-farm-style channels, and lean towards in-depth, insightful content. "
        "Provide your response *only* as a single JSON object "
        "with one key: \"Youtube_queries\", where the value is a list of the requested query strings. "
        "Do not include any other explanatory text, greetings, or markdown formatting outside the JSON object itself."
    )
    context_for_diversity = ""
    if existing_queries_today:
        context_for_diversity = (
            "To ensure variety, I have already explored topics related to these queries today:\n"
            + "\n".join([f"- \"{q}\"" for q in existing_queries_today]) + "\n"
            "Please provide queries that explore *different facets* or *new angles* of my interests relative to these."
        )
    user_prompt = (
        f"My interest profile is as follows:\n{interest_profile_description}\n\n"
        f"{context_for_diversity}\n"
        f"Based on this interest profile, please generate exactly {num_queries_to_generate} diverse and effective search query strings "
        "that I can use to find relevant and engaging videos on YouTube. "
        "These queries should cover different aspects of my stated interests, aiming for a mix of specific technical topics, "
        "broader concepts, project showcases, or expert discussions that are both **interesting and technically informative**. "
        "Crucially, these queries should be crafted to help discover videos from independent creators, hobbyists, or smaller channels "
        "that offer unique, authentic, and technically rich perspectives, rather than large media organizations or content farms. "
        "Each query should be a concise string, typically 2-6 words long. "
        "Remember, your entire response must be a single JSON object: {\"Youtube_queries\": [\"query1\", \"query2\", ...]}."
    )

    response_data = call_claude_api(system_prompt, user_prompt, max_tokens)
    if response_data and response_data.get('content') and response_data['content'][0].get('type') == 'text':
        claude_text = response_data['content'][0]['text']
        parsed_json = extract_json_from_claude_response(claude_text)
        if parsed_json and isinstance(parsed_json, dict):
            queries = parsed_json.get("Youtube_queries")
            if queries and isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                print(f"Claude generated Youtube queries: {queries}")
                return queries
            else:
                print("Error: 'Youtube_queries' key not found or invalid format in Claude's parsed JSON.")
                print(f"Parsed JSON: {parsed_json}")
        else:
             print(f"Error: Could not parse valid JSON dictionary from Claude's response for queries. Claude raw text: {claude_text[:500]}")
    else:
        print(f"Error: Invalid or empty response from Claude for search query generation. Response: {response_data}")
    return []


def generate_post_content_with_claude(interest_profile_desc, youtube_video_snippet, max_tokens, existing_posts_context=""):
    """
    Generates both a title and an HN-style comment for a YouTube video using a single Claude API call.
    Returns a tuple (title, comment) or (None, None) if generation fails.
    """
    if not youtube_video_snippet: return None, None
    video_title = youtube_video_snippet.get('title', 'N/A')
    video_description_snippet = youtube_video_snippet.get('description', 'N/A')[:300]
    channel_title = youtube_video_snippet.get('channelTitle', 'N/A')
    video_id = youtube_video_snippet.get('videoId', '')
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    system_prompt = (
        "You are a creative assistant and insightful commentator, specializing in crafting content in the style of Hacker News (HN).\n"
        "Your task is to generate:\n"
        "1. A Hacker News-style title for a blog post about the provided YouTube video. **This title should be faithful to the original video's title and description, capturing its core subject or key takeaway.** Rephrase this essence into a concise, intriguing, and factual HN-style title. HN titles often highlight a core problem, a surprising discovery, a technical achievement, or a unique perspective. They avoid excessive hype or clickbait. The title should make someone want to know more. Examples: 'Show HN: I built X to solve Y', 'The Unreasonable Effectiveness of Z', 'Ask HN: How do you deal with A?', 'Why B is more complex than it seems'.\n"
        "2. A concise (1-3 sentences) Hacker News-style comment about the same video, explaining its relevance or an interesting technical takeaway, based on the user's interests. If the video appears to be from an independent creator or offers a unique, non-mainstream, and technically valuable perspective, try to subtly highlight that aspect.\n\n"
        "Your entire response MUST BE a single JSON object with two keys:\n"
        "- \"title\": A string value for the generated title. The title must be plain text and JSON-safe.\n"
        "- \"hn_comment\": A string value for the generated comment.\n\n"
        "Do not include any other explanatory text, greetings, or markdown formatting outside the JSON object itself."
    )

    context_info = "When crafting the title and comment, try to make them distinct and complementary if there are existing posts today."
    if existing_posts_context and existing_posts_context != "No posts yet today." and existing_posts_context != "No existing titles for today.": # Handle both phrasings
        context_info = (
            f"Here's some context about posts already made today (titles/themes):\n{existing_posts_context}\n\n"
            "When crafting the new title and comment, try to make them distinct and complementary to these existing items, "
            "contributing to an overall eclectic and interesting set of content."
        )

    interest_prompt_part = f"My guiding interest profile for this task is: \"{interest_profile_desc.strip()}\"\n\n" if interest_profile_desc else ""

    user_prompt = (
        f"{interest_prompt_part}"
        f"The YouTube video details are:\n"
        f"Original Title: {video_title}\n"
        f"Channel: {channel_title}\n"
        f"Description (first 300 chars): {video_description_snippet}\n"
        f"URL: {video_url}\n\n"
        f"{context_info}\n\n"
        "Please generate the title and comment as per the required JSON format. "
        "For the title, craft it in the style of Hacker News. **Crucially, ensure the title is faithful to the original video's title and description by extracting its main topic or key information and rephrasing it.** Make it concise, intriguing, and focused on the core interesting aspect of the video. It might pose a question, state a surprising fact, or hint at a technical challenge or solution. "
        "The comment should explain why THIS video is interesting and technically relevant, particularly considering my stated interests and a preference for content from independent or niche creators that delve into technical details or unique insights. "
        "If the video seems to be from such a source and offers good technical content, reflect that appreciation in your tone or focus. "
        "Remember, your entire response must be ONLY the JSON object: {\"title\": \"your generated title\", \"hn_comment\": \"your generated comment\"}."
    )

    print(f"\nRequesting post content (title & comment) from Claude for video: {video_title}...")
    response_data = call_claude_api(system_prompt, user_prompt, max_tokens)

    if response_data and response_data.get('content') and response_data['content'][0].get('type') == 'text':
        claude_text = response_data['content'][0]['text']
        parsed_json = extract_json_from_claude_response(claude_text)

        if parsed_json and isinstance(parsed_json, dict):
            generated_title = parsed_json.get("title")
            hn_comment = parsed_json.get("hn_comment")

            if generated_title and isinstance(generated_title, str) and hn_comment and isinstance(hn_comment, str):
                # Remove surrounding quotes if Claude adds them to the title
                generated_title = re.sub(r'^["\']|["\']$', '', generated_title.strip())
                if not generated_title:
                    print(f"Error: Claude returned an empty title in the JSON. Raw text: {claude_text}")
                    return None, None
                print(f"Claude generated title: {generated_title}")
                print(f"Claude generated HN-Style Comment: {hn_comment}")
                return generated_title.strip(), hn_comment.strip()
            else:
                missing_keys = []
                if not generated_title or not isinstance(generated_title, str): missing_keys.append("'title' (string)")
                if not hn_comment or not isinstance(hn_comment, str): missing_keys.append("'hn_comment' (string)")
                print(f"Error: Missing or invalid keys ({', '.join(missing_keys)}) in Claude's parsed JSON for post content.")
                print(f"Parsed JSON: {parsed_json}")
        else:
            print(f"Error: Could not parse valid JSON dictionary from Claude's response for post content. Claude raw text: {claude_text[:500]}")
    else:
        print(f"Error: Invalid or empty response from Claude for post content generation. Response: {response_data}")
    return None, None


# --- Main Application Logic (largely unchanged, but calls Claude functions) ---
def add_post_to_daily_json(post_title, post_url, hn_comment_text=None, source_bot="YouTubeBot_ClaudeQuery"): # Updated source_bot
    now = datetime.now()
    filename = get_todays_json_filename()
    creation_time_str = now.strftime("%I:%M %p")
    posts = load_todays_posts(filename)
    new_post_id = max((p.get("id", 0) for p in posts if isinstance(p, dict)), default=0) + 1
    post_comments = []
    if hn_comment_text:
        post_comments.append({
            "id": f"c_claude_hn_{new_post_id}_1", "author": "ClaudeHNBot", # Updated author
            "text": hn_comment_text, "time_ago": creation_time_str, "heart": 0, "comments": []
        })
    new_post = {
        "id": new_post_id, "title": post_title, "url": post_url, "points": 0,
        "author": source_bot, "time_ago": creation_time_str, "heart": 0,
        "comments_count": len(post_comments), "comments": post_comments, "source_type": "video"
    }
    posts.append(new_post)
    try:
        with open(filename, 'w') as f: json.dump(posts, f, indent=2)
        print(f"\nAdded video post '{post_title}' to {filename}")
    except IOError: print(f"Error writing to {filename}.")

def is_video_already_posted(video_url, todays_posts):
    return any(isinstance(p, dict) and p.get('url') == video_url for p in todays_posts)

def is_video_within_duration(video_details, duration_filter_config):
    if not duration_filter_config or not video_details: return True
    duration_iso = video_details.get('contentDetails', {}).get('duration')
    if not duration_iso: return True
    try:
        duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
        min_sec = duration_filter_config.get("min_seconds")
        max_sec = duration_filter_config.get("max_seconds")
        if min_sec is not None and duration_seconds < min_sec: return False
        if max_sec is not None and duration_seconds > max_sec: return False
    except Exception: return True
    return True

# NEW: Function to save JSON data to a file
def save_json_file(data, filename, success_message_prefix=""):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        if success_message_prefix:
            print(f"Info: {success_message_prefix} saved to '{filename}'.")
        return True
    except IOError as e:
        print(f"Error: Could not write to {filename}. {e}")
    except TypeError as e:
        print(f"Error: Could not serialize data to JSON for {filename}. {e}")
    return False

# NEW: Function to fetch raw text content from a URL
def fetch_text_from_url(url):
    print(f"Fetching recent interests from: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        print("Successfully fetched recent interests.")
        return response.text
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error fetching URL {url}: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error fetching URL {url}: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred fetching URL {url}: {e}")
    return None

# NEW: Claude function to mutate the interest prompt
def mutate_prompt_with_claude(current_mutable_desc, recent_notes_text, core_interest_desc, max_tokens):
    system_prompt = (
        "You are an AI assistant specializing in refining and evolving a user's interest profiles. "
        "Your task is to synthesize a new, concise 'evolving focus' description (for a mutable interest prompt). "
        "This new description should integrate key themes or ideas from the user's 'recent notes/thoughts', "
        "while remaining aligned with their 'core interest' and the 'current evolving focus'. "
        "The output should be a single paragraph that represents the updated evolving focus. "
        "Your entire response MUST BE a single JSON object with one key: \"mutated_prompt_description\", "
        "where the value is the new description text. Do not include any other explanatory text."
    )
    user_prompt = (
        f"Here is the user's information:\n\n"
        f"1. Core Interest (provides overall context and long-term goals):\n\"\"\"\n{core_interest_desc}\n\"\"\"\n\n"
        f"2. Current Evolving Focus (the prompt part to be updated):\n\"\"\"\n{current_mutable_desc}\n\"\"\"\n\n"
        f"3. Recent Notes/Thoughts (new inputs to incorporate or reflect):\n\"\"\"\n{recent_notes_text}\n\"\"\"\n\n"
        "Please synthesize these into an updated 'evolving focus' description. "
        "It should be a natural evolution of the current focus, informed by the recent notes, and consistent with the core interest. "
        "Focus on clarity, conciseness, and capturing the essence of the evolution. "
        "Remember, provide ONLY the JSON: {\"mutated_prompt_description\": \"new_description_text\"}."
    )
    print("\nCalling Claude API to mutate interest prompt...")
    response_data = call_claude_api(system_prompt, user_prompt, max_tokens)

    if response_data and response_data.get('content') and response_data['content'][0].get('type') == 'text':
        claude_text = response_data['content'][0]['text']
        parsed_json = extract_json_from_claude_response(claude_text)
        if parsed_json and isinstance(parsed_json, dict):
            new_description = parsed_json.get("mutated_prompt_description")
            if new_description and isinstance(new_description, str):
                print(f"Claude successfully mutated prompt description:\n{new_description}")
                return new_description.strip()
            else:
                print("Error: 'mutated_prompt_description' key not found or invalid format in Claude's parsed JSON.")
                print(f"Parsed JSON: {parsed_json}")
        else:
            print(f"Error: Could not parse valid JSON dictionary from Claude's response for prompt mutation. Claude raw text: {claude_text[:500]}")
    else:
        print(f"Error: Invalid or empty response from Claude for prompt mutation. Response: {response_data}")
    return None

if __name__ == "__main__":
    print("--- YouTube Content Bot (Claude Query Generation, Hardcoded Params) Starting ---")

    youtube_interests_data = load_youtube_interests()
    if not youtube_interests_data:
        print("Exiting: Missing youtube_interests.json.")
        exit(1)
    
    general_prompts_data = load_general_prompts() 
    if not general_prompts_data: general_prompts_data = {}

    # --- Attempt to mutate the mutable prompt ---
    recent_notes = fetch_text_from_url(RECENT_INTERESTS_URL)
    
    # Ensure there's at least one immutable prompt for context
    core_interest_for_mutation = None
    if youtube_interests_data.get("immutable_prompts"):
        core_interest_for_mutation = random.choice(youtube_interests_data["immutable_prompts"])['description']

    if recent_notes and core_interest_for_mutation and youtube_interests_data.get("mutable_prompts"):
        # Assuming we mutate the first mutable prompt if multiple exist
        mutable_prompt_object = youtube_interests_data["mutable_prompts"][0]
        original_mutable_description = mutable_prompt_object.get("description")

        if original_mutable_description:
            mutation_config = YOUTUBE_BOT_PARAMETERS.get("claude_prompt_mutation", {})
            mutation_max_tokens = mutation_config.get("max_tokens", 300)
            
            print(f"\nAttempting to mutate mutable prompt ID: {mutable_prompt_object.get('id', 'N/A')}")
            new_mutable_description = mutate_prompt_with_claude(
                original_mutable_description,
                recent_notes,
                core_interest_for_mutation,
                mutation_max_tokens
            )
            if new_mutable_description and new_mutable_description != original_mutable_description:
                youtube_interests_data["mutable_prompts"][0]["description"] = new_mutable_description
                if save_json_file(youtube_interests_data, YOUTUBE_INTERESTS_FILE, "Updated YouTube interests"):
                    print("Successfully saved mutated prompt to youtube_interests.json.")
                else:
                    print("Warning: Failed to save mutated prompt. Using it for this session only.")
            elif new_mutable_description == original_mutable_description:
                print("Info: Mutated prompt is identical to the original. No changes made.")
            else:
                print("Info: Prompt mutation failed or returned no new description. Using original mutable prompt.")
        else:
            print("Info: No description found in the first mutable prompt to mutate.")
    elif not recent_notes:
        print("Info: Could not fetch recent notes. Skipping prompt mutation.")
    elif not core_interest_for_mutation:
        print("Info: No core immutable interest found for context. Skipping prompt mutation.")
    else:
        print("Info: No mutable prompts found in youtube_interests.json to mutate.")
    # --- End of prompt mutation ---

    # Re-extract descriptions after potential mutation for the current run
    yt_immutable_descs = [p['description'] for p in youtube_interests_data.get("immutable_prompts", []) if p.get('description')]
    yt_mutable_descs = [p['description'] for p in youtube_interests_data.get("mutable_prompts", []) if p.get('description')]
    
    youtube_interest_profile_parts = []
    if yt_immutable_descs:
        youtube_interest_profile_parts.append(f"Core Youtube Interests: \"{random.choice(yt_immutable_descs)}\"")
    if yt_mutable_descs:
        youtube_interest_profile_parts.append(f"Evolving Youtube Focus: \"{random.choice(yt_mutable_descs)}\"")

    if not youtube_interest_profile_parts:
        print("Error: No descriptions found in youtube_interests.json. Cannot generate queries.")
        exit(1)
    
    Youtube_interest_profile = "\n\n".join(youtube_interest_profile_parts)
    print(f"\nUsing Youtube Interest Profile:\n{Youtube_interest_profile}\n" + "-"*30)
    title_comment_interest_profile = Youtube_interest_profile # Using same profile for all Claude tasks

    todays_json_filename = get_todays_json_filename()
    todays_posts_data = load_todays_posts(todays_json_filename)
    
    # Consolidate context string for Claude
    todays_context_for_claude = "No posts yet today."
    if todays_posts_data:
        post_titles = [p.get('title', "N/A") for p in todays_posts_data if isinstance(p, dict) and p.get('title')]
        if post_titles:
            summary_list = [f"- \"{title}\"" for title in post_titles]
            todays_context_for_claude = "\n".join(summary_list)
    
    duration_filter_cfg = YOUTUBE_BOT_PARAMETERS["video_duration_filter"]
    claude_query_gen_config = YOUTUBE_BOT_PARAMETERS["claude_query_generation"]
    num_queries = claude_query_gen_config.get("num_queries_to_generate", 3)
    query_max_tokens = claude_query_gen_config.get("max_tokens", 500)
    
    post_content_gen_config = YOUTUBE_BOT_PARAMETERS["claude_post_content_generation"] # MODIFIED
    post_content_max_tokens = post_content_gen_config.get("max_tokens", 450) # MODIFIED

    search_defaults = YOUTUBE_BOT_PARAMETERS["Youtube_defaults"]
    max_results_fetch = search_defaults.get("max_results_per_fetch", 3)
    post_limit_per_query = search_defaults.get("post_limit_per_generated_query", 1)
    default_order_by = search_defaults.get("order_by", "relevance")
    max_total_posts_this_run = YOUTUBE_BOT_PARAMETERS["max_total_posts_per_run"]

    generated_search_queries = generate_Youtube_queries_with_claude(
        Youtube_interest_profile, 
        num_queries,
        query_max_tokens,
        # Pass context of today's posts if you want queries to be diverse from them
        # For now, not passing existing queries, but could use todays_context_for_claude
        # if the query generation prompt was adapted to use it.
    )

    if not generated_search_queries:
        print("No search queries generated by Claude. Exiting.")
        exit(1)

    processed_videos_count = 0
    print("\n--- Processing Claude-Generated Youtube Queries ---")
    for query_text in generated_search_queries:
        if processed_videos_count >= max_total_posts_this_run:
            print(f"Reached overall post limit ({max_total_posts_this_run}). Stopping query processing.")
            break
        
        print(f"\nProcessing Claude-generated query: \"{query_text}\"")
        videos = search_youtube_videos(query_text, max_results=max_results_fetch, order_by=default_order_by)
        
        query_posted_count = 0
        for video_item in videos:
            if processed_videos_count >= max_total_posts_this_run: break
            if query_posted_count >= post_limit_per_query:
                print(f"Reached post limit for query '{query_text}'.")
                break

            video_id = video_item.get("id", {}).get("videoId")
            if not video_id: continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            if is_video_already_posted(video_url, todays_posts_data):
                print(f"Video from query '{query_text}' already posted: {video_url}. Skipping.")
                continue
            
            full_video_details = get_video_details(video_id)
            if not full_video_details: continue
            if not is_video_within_duration(full_video_details, duration_filter_cfg): continue

            video_snippet_for_claude = full_video_details.get("snippet", {})
            video_snippet_for_claude['videoId'] = video_id 
            video_snippet_for_claude['description'] = video_snippet_for_claude.get('description', '') # Ensure description is present

            # MODIFIED: Call the new combined function
            generated_title, hn_comment = generate_post_content_with_claude(
                title_comment_interest_profile, # Using the same interest profile
                video_snippet_for_claude,
                post_content_max_tokens,
                todays_context_for_claude
            )

            if generated_title and hn_comment:
                add_post_to_daily_json(generated_title, video_url, hn_comment)
                
                # Update context for any subsequent (though unlikely with max_total_posts_per_run=1) operations
                todays_posts_data.append({"url": video_url, "title": generated_title}) # Add to in-memory list
                current_titles = [p.get('title', "N/A") for p in todays_posts_data if isinstance(p,dict) and p.get('title')]
                if current_titles:
                    todays_context_for_claude = "\n".join([f"- \"{t}\"" for t in current_titles])
                
                processed_videos_count += 1
                query_posted_count += 1
            else:
                print(f"Could not generate title and/or comment for video from query '{query_text}'. Skipping.")

    print(f"\n--- YouTube Content Bot Finished. Posted {processed_videos_count} new videos using Claude. ---")
