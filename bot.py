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
    return "Bot is running", 200

# ===== PARMAR ACADEMY API =====
HOST = "https://parmaracademyapi.classx.co.in"
HEADERS = {
    "Authorization": os.getenv("AUTHORIZATION"),
    "User-Agent": "Mozilla/5.0",
    "Auth-Key": "appxapi"
}

def get_all_courses():
    """Get all available courses"""
    try:
        res = requests.get(
            f"{HOST}/get/courselist?exam_name=&start=0",
            headers=HEADERS,
            timeout=10
        )
        return res.json().get("data", [])
    except Exception:
        return []

def get_subjects(course_id):
    """Get subjects for a course"""
    try:
        res = requests.get(
            f"{HOST}/get/allsubjectfrmlivecourseclass?courseid={course_id}&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return res.json().get("data", [])
    except Exception:
        return []

def get_topics(course_id, subject_id):
    """Get topics for a subject"""
    try:
        res = requests.get(
            f"{HOST}/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return res.json().get("data", [])
    except Exception:
        return []

def get_videos(course_id, subject_id, topic_id):
    """Get videos for a topic"""
    try:
        res = requests.get(
            f"{HOST}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&windowsapp=false&start=-1",
            headers=HEADERS,
            timeout=10
        )
        return [v for v in res.json().get("data", []) if v.get("material_type") == "VIDEO"]
    except Exception:
        return []

def get_video_token(course_id, video_id):
    """Get playback token for a video"""
    try:
        res = requests.get(
            f"{HOST}/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0",
            headers=HEADERS,
            timeout=10
        )
        return res.json()["data"]["video_player_token"]
    except Exception:
        return None

# Initialize Pyrogram
bot = Client(
    "parmar_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN")
)

# Import handlers after bot is defined
from bot_handlers import *

if __name__ == "__main__":
    import threading
    # Start Flask health check
    threading.Thread(
        target=app.run,
        kwargs={'host': '0.0.0.0', 'port': 8000}
    ).start()
    # Start Telegram bot
    bot.run()
