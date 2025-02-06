#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.requests python3Packages.feedparser python3Packages.python-dotenv python3Packages.anthropic python3Packages.openai
import feedparser
import time
import os
import random
import json
from anthropic import Anthropic
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "NPR News": "https://feeds.npr.org/1001/rss.xml",
    "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "SF Local": "https://news.google.com/rss/search?q=san+francisco+weather+traffic+when:1d&hl=en-US&gl=US&ceid=US:en"
}

# Add list of available voices
TTS_VOICES = ['alloy', 'ash', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer']

def get_headlines():
    all_headlines = {
        "news": [],
        "weather": [],
        "traffic": []
    }
    
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if source == "SF Local":
                print("\nDebug - SF Local News:")
                for entry in feed.entries[:10]:
                    title = entry.title.lower()
                    if 'weather' in title:
                        all_headlines["weather"].append(entry.title)
                        print(f"Weather: {entry.title}")
                    elif any(word in title for word in ['traffic', 'road', 'highway', 'bridge']):
                        all_headlines["traffic"].append(entry.title)
                        print(f"Traffic: {entry.title}")
                
                # Fallbacks if we don't get enough headlines
                if not all_headlines["weather"]:
                    all_headlines["weather"] = ["The fog speaks in riddles today"]
                if not all_headlines["traffic"]:
                    all_headlines["traffic"] = ["The roads are hungry"]
            else:
                # Get first 2 entries from each news source
                for entry in feed.entries[:2]:
                    all_headlines["news"].append(f"{source}: {entry.title}")
        except Exception as e:
            print(f"Error fetching {source}: {e}")
        
        time.sleep(1)
    
    return all_headlines

def get_weird_summary(headlines):
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Load and select random prompt
    with open('prompts.json', 'r') as f:
        prompt_data = json.load(f)
        selected_prompt = random.choice(prompt_data['prompts'])
    
    prompt = selected_prompt['prompt'] + """

    News Headlines:
    {}
    
    Weather:
    {}
    
    Traffic:
    {}
    """.format(
        '\n'.join(headlines["news"]),
        '\n'.join(headlines["weather"][:3]),
        '\n'.join(headlines["traffic"][:3])
    )

    print(f"\nUsing prompt style: {selected_prompt['name']}")
    print("\nSending this prompt to Claude:\n")
    print("-" * 50)
    print(prompt)
    print("-" * 50 + "\n")

    message = client.messages.create(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="claude-3-5-sonnet-latest",
    )
    
    return message.content[0].text

def create_radio_broadcast(text):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create output directory if it doesn't exist
        output_dir = Path(__file__).parent / "broadcasts"
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        
        # Randomly select a voice
        voice = random.choice(TTS_VOICES)
        speech_file_path = output_dir / f"klon_radio_{voice}_{timestamp}.mp3"
        
        print(f"\nGenerating radio broadcast audio with voice: {voice}...")
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        
        response.stream_to_file(speech_file_path)
        print(f"Broadcast saved to: {speech_file_path}")
        
    except Exception as e:
        print(f"Error creating audio broadcast: {e}")
        print(f"Text that failed: {text}")

def main():
    print("Tuning in to K.L.O.N. Radio...")
    headlines = get_headlines()
    
    print("\nTransmitting to Claude...\n")
    weird_broadcast = get_weird_summary(headlines)
    
    print("=" * 50)
    print("\nK.L.O.N. RADIO - SF DESERT FREQUENCIES\n")
    print(weird_broadcast)
    print("\n" + "=" * 50)
    
    # Create audio version
    create_radio_broadcast(weird_broadcast)

if __name__ == "__main__":
    main() 
