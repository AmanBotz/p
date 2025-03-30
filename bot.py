import os
import re
import json
import base64
import hashlib
import threading
from pyrogram import Client, filters
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import m3u8
import requests
from flask import Flask

app = Flask(__name__)

# ===== CONFIG =====
USER_ID = os.getenv("USER_ID")
AUTHORIZATION = os.getenv("AUTHORIZATION")
HOST = "https://parmaracademyapi.classx.co.in"
API_ID = int(os.getenv("API_ID"))  # Convert to integer here
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

HEADERS = {
    "Authorization": AUTHORIZATION,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Origin": "https://www.parmaracademy.in",
    "Referer": "https://www.parmaracademy.in/",
    "Auth-Key": "appxapi"
}

# ===== FLASK HEALTH CHECK =====
@app.route('/')
def health_check():
    return "Bot is running", 200

# ===== TELEGRAM BOT =====
bot = Client(
    "parmar_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ===== CORE FUNCTIONS =====
def get_all_courses():
    res = requests.get(f"{HOST}/get/courselist?exam_name=&start=0", headers=HEADERS)
    return res.json()["data"]

def get_subjects(course_id):
    res = requests.get(f"{HOST}/get/allsubjectfrmlivecourseclass?courseid={course_id}&start=-1", headers=HEADERS)
    return res.json()["data"]

def get_topics(course_id, subject_id):
    res = requests.get(f"{HOST}/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1", headers=HEADERS)
    return res.json()["data"]

def get_videos(course_id, subject_id, topic_id):
    res = requests.get(f"{HOST}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&windowsapp=false&start=-1", headers=HEADERS)
    return [v for v in res.json()["data"] if v["material_type"] == "VIDEO"]

def get_video_token(course_id, video_id):
    res = requests.get(f"{HOST}/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0", headers=HEADERS)
    return res.json()["data"]["video_player_token"]

def get_video_html(token):
    return requests.get(f"https://player.akamai.net.in/secure-player?token={token}&watermark=").text

def get_quality_options(html):
    data = json.loads(re.search(r'<script id="__NEXT_DATA__".*?>(.*?)</script>', html).group(1))
    return [q["quality"] for q in data["props"]["pageProps"]["urls"]]

# ===== BOT HANDLERS =====
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Welcome to Parmar Academy Downloader!\nUse /courses to begin")

@bot.on_message(filters.command("courses"))
async def list_courses(client, message):
    courses = get_all_courses()
    reply = "Available Courses:\n"
    for i, course in enumerate(courses, 1):
        reply += f"{i}. {course['course_name']}\n"
    await message.reply(reply)

if __name__ == "__main__":
    import threading
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8000}).start()
    bot.run()
