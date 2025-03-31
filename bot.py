import os
import requests
from pyrogram import Client
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask for health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot Operational ✅", 200

# ===== PARMAR ACADEMY API INTEGRATION =====
HOST = "https://parmaracademyapi.classx.co.in"
HEADERS = {
    "Authorization": os.getenv("AUTHORIZATION"),
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Auth-Key": "appxapi"
}

def get_all_courses():
    """Fetch available courses with error handling"""
    try:
        response = requests.get(
            f"{HOST}/get/courselist?exam_name=&start=0",
            headers=HEADERS,
            timeout=10
        )
        return response.json().get("data", [])
    except Exception as e:
        print(f"Course fetch error: {str(e)}")
        return []

def get_subjects(course_id: str):
    """Fetch subjects for a course"""
    try:
        response = requests.get(
            f"{HOST}/get/allsubjectfrmlivecourseclass?courseid={course_id}&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return response.json().get("data", [])
    except Exception as e:
        print(f"Subject fetch error: {str(e)}")
        return []

def get_topics(course_id: str, subject_id: str):
    """Fetch topics for a subject"""
    try:
        response = requests.get(
            f"{HOST}/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return response.json().get("data", [])
    except Exception as e:
        print(f"Topic fetch error: {str(e)}")
        return []

# Add this function to bot.py
def get_videos(course_id: str, subject_id: str, topic_id: str):
    """Fetch videos for a topic"""
    try:
        response = requests.get(
            f"{HOST}/get/livecourseclassbycoursesubtopconceptapiv3?"
            f"courseid={course_id}&subjectid={subject_id}"
            f"&topicid={topic_id}&conceptid=&windowsapp=false&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return [
            {
                "id": v["id"],
                "title": v.get("Title", "Untitled"),
                "video_id": v.get("videoid") or v.get("id")  # Critical fix
            } 
            for v in response.json().get("data", []) 
            if v.get("material_type") == "VIDEO"
        ]
    except Exception as e:
        print(f"Video fetch error: {str(e)}")
        return []

def get_video_token(course_id: str, video_id: str):
    """Get video decryption token"""
    try:
        response = requests.get(
            f"{HOST}/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0",
            headers=HEADERS,
            timeout=10
        )
        return response.json()["data"]["video_player_token"]
    except Exception as e:
        print(f"Token fetch error: {str(e)}")
        return None

# Initialize Pyrogram Client
bot = Client(
    name="parmar_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Import handlers after bot initialization
from bot_handlers import *

if __name__ == "__main__":
    import threading
    # Start Flask server for health checks
    threading.Thread(
        target=app.run,
        kwargs={'host': '0.0.0.0', 'port': 8000}
    ).start()
    
    # Start Telegram Bot
    print("Bot is starting...")
    bot.run()
    print("Bot stopped")
