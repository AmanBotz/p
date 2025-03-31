import os
import re
import time
import shutil
import json
import base64
import hashlib
import threading
import logging
from functools import partial
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from flask import Flask
import requests as req
from Crypto.Cipher import AES
import m3u8
from moviepy.editor import VideoFileClip
import tempfile

# Import your existing functions from the original script here
# [Include all the functions from the original code up to handle_download_start]
# -------------------- CONFIGURATION --------------------
user_id = "455000"
authorization = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjQ1NTAwMCIsImVtYWlsIjoiYWJoaS5ibXNjZTIwMTRAZ21haWwuY29tIiwidGltZXN0YW1wIjoxNzQzNDA2ODEzLCJ0ZW5hbnRUeXBlIjoidXNlciIsInRlbmFudE5hbWUiOiIiLCJ0ZW5hbnRJZCI6IiIsImRpc3Bvc2FibGUiOmZhbHNlfQ.06SQlx72dLpdacvPpXT8t0Ic7DRvKvakBHuzodhUunI"
host = "https://parmaracademyapi.classx.co.in"
headers = {
    "Authorization": authorization,
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/133.0.0.0 Safari/537.36"),
    "Origin": "https://www.parmaracademy.in",
    "Referer": "https://www.parmaracademy.in/",
    "Sec-Ch-Ua-Platform": "Windows",
    "Auth-Key": "appxapi",
    "Client-Service": "Appx",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

# -------------------- MAIN.PY FUNCTIONS (HTML Download) --------------------
def get_all_purchases():
    url = host + f"/get/courselist?exam_name=&start=0"
    res = req.get(url, headers=headers).json()
    return res["data"]

def get_titles(course_id):
    url = host + f"/get/allsubjectfrmlivecourseclass?courseid={course_id}&start=0"
    res = req.get(url, headers=headers).json() 
    return res["data"]

# Original function definition - CORRECT THE TYPO
def get_titles_of_topic(course_id, subject_id):  # Changed from "toipic" to "topic"
    url = host + f"/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1"
    res = req.get(url, headers=headers).json() 
    return res["data"]

def get_all_video_links(course_id, subject_id, topic_id):
    url = (host + f"/get/livecourseclassbycoursesubtopconceptapiv3?"
           f"courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&windowsapp=false&start=-1")
    res = req.get(url, headers=headers).json()
    return res["data"]

def get_video_token(course_id, video_id):
    url = host + f"/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0&folder_wise_course=0"
    res = req.get(url, headers=headers).json()
    token = res["data"]["video_player_token"]
    return token

def get_video_html(token):
    url = f"https://player.akamai.net.in/secure-player?token={token}&watermark="
    return req.get(url, headers=headers).text

# -------------------- MAIN1.PY FUNCTIONS (Video Downloading) --------------------
def watch_video(course_id, video_id):
    headers2 = headers.copy()
    headers2["content-type"] = "application/x-www-form-urlencoded"
    data = f"user_id={user_id}&course_id={course_id}&live_course_id={video_id}&ytFlag=0&folder_wise_course=0"
    try:
        req.post(host + f"/post/watch_videov2", data=data, headers=headers2).json()
    except Exception as e:
        print("Watch video error:", e)

def get_data_enc_key(time_val, token):
    n = time_val[-4:]
    r = int(n[0])
    i = int(n[1:3])
    o = int(n[3])
    a = time_val + token[r:i]
    s = hashlib.sha256()
    s.update(a.encode('utf-8'))
    c = s.digest()
    if o == 6:
        sign = c[:16]
    elif o == 7:
        sign = c[:24]
    else:
        sign = c
    key = base64.b64encode(sign).decode('utf-8')
    return key

def decrypt_data(data, key, ivb):
    i = base64.b64decode(key)
    o = base64.b64decode(ivb)
    a = base64.b64decode(data)
    cipher = AES.new(i, AES.MODE_CBC, o)
    decrypted = cipher.decrypt(a)
    try:
        return decrypted.decode('utf-8')
    except:
        return decrypted

def decode_video_tsa(input_string):
    shift_value = 0xa * 0x2
    result = ''.join(chr(ord(c) - shift_value) for c in input_string)
    return base64.b64decode(result)

def decode_video_tsb(input_string):
    xor_value = 0x3
    shift_value = 0x2a
    result = ''.join(chr((ord(c) >> xor_value) ^ shift_value) for c in input_string)
    return base64.b64decode(result)

def decode_video_tsc(input_string):
    shift_value = 0xa
    result = ''.join(chr(ord(c) - shift_value) for c in input_string)
    return base64.b64decode(result)

def decode_video_tsd(input_string):
    shift_value = 0x2
    result = ''.join(chr(ord(c) >> shift_value) for c in input_string)
    return base64.b64decode(result)

def decode_video_tse(input_string):
    xor_value = 0x3
    shift_value = 0x2a
    result = ''.join(chr((ord(c) ^ shift_value) >> xor_value) for c in input_string)
    return base64.b64decode(result)

def get_file_extension(url):
    match = re.search(r'\.\w+$', url)
    return match.group(0)[1:] if match else None

total_segments = 0
current_segment = 0

def download_and_decrypt_segment(segment_url, key, iv, output_path):
    global current_segment
    if os.path.exists(output_path):
        current_segment += 1
        print(f"Downloaded segments: {current_segment}/{total_segments}", end="\r")
        return
    attempt = 0
    segment_data = None
    while attempt <= 5:
        try:
            response = req.get(segment_url, stream=True, timeout=15)
            response.raise_for_status()
            segment_data = response.content
            break
        except Exception as e:
            attempt += 1
    if not segment_data:
        print(f"Failed to download segment: {segment_url}")
        return
    ext = get_file_extension(segment_url)
    if ext == "tsa":
        segment_data = decode_video_tsa(segment_data.decode("utf-8"))
    elif ext == "tsb":
        segment_data = decode_video_tsb(segment_data.decode("utf-8"))
    elif ext == "tsc":
        segment_data = decode_video_tsc(segment_data.decode("utf-8"))
    elif ext == "tsd":
        segment_data = decode_video_tsd(segment_data.decode("utf-8"))
    elif ext == "tse":
        segment_data = decode_video_tse(segment_data.decode("utf-8"))
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_segment = cipher.decrypt(segment_data)
    temp_file = output_path + ".bak"
    with open(temp_file, "wb") as f:
        f.write(decrypted_segment)
    os.rename(temp_file, output_path)
    current_segment += 1
    print(f"Downloaded segment: {current_segment}/{total_segments}", end="\r")

def download_m3u8_playlist(playlist, output_file, key, directory, max_thread=1, max_segment=1):
    os.makedirs(directory, exist_ok=True)
    print(f"\nDownloading video segments into: {output_file}")
    if not playlist.segments:
        raise ValueError("No segments found in the playlist")
    segment_files = []
    global total_segments, current_segment
    current_segment = 0
    total_segments = len(playlist.segments)
    for i in range(0, len(playlist.segments), max_thread):
        threads = []
        batch = playlist.segments[i:i + max_thread]
        for j, segment in enumerate(batch):
            if max_segment and (i+j) >= max_segment:
                break
            segment_url = segment.uri
            segment_file = f"segment_{i+j}.ts"
            segment_files.append(segment_file)
            iv = None
            if segment.key and segment.key.method == "AES-128" and segment.key.iv:
                iv = bytes.fromhex(segment.key.iv[2:])
            thread = threading.Thread(target=download_and_decrypt_segment,
                                      args=(segment_url, key, iv, os.path.join(directory, segment_file)))
            threads.append(thread)
            thread.start()
        for t in threads:
            t.join()
    if current_segment != len(segment_files):
        print("Not all segments were downloaded successfully.")
        return
    temp_out = output_file + ".bak"
    with open(temp_out, "wb") as out_f:
        for segment_file in segment_files:
            seg_path = os.path.join(directory, segment_file)
            with open(seg_path, "rb") as seg_f:
                out_f.write(seg_f.read())
            os.remove(seg_path)
    os.rename(temp_out, output_file)
    print(f"\nVideo saved as {output_file}")

async def handle_download_start(context, html_path, output_base, chat_id, message_id):
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        pattern = r'<script[^>]* id="__NEXT_DATA__"[^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            await context.bot.edit_message_text("❌ Failed to parse video data", chat_id, message_id)
            return

        decoded = json.loads(match.group(1).strip())["props"]["pageProps"]
        datetime_str = decoded.get("datetime", "")
        token_val = decoded.get("token", "")
        iv = decoded.get("ivb6", "")
        urls = decoded.get("urls", [])

        if not (datetime_str and token_val and iv and urls):
            await context.bot.edit_message_text("❌ Missing video decryption parameters", chat_id, message_id)
            return

        data_dec_key = get_data_enc_key(datetime_str, token_val)
        selected_quality = context.user_data.get("selected_quality", 0)

        try:
            video_info = urls[selected_quality]
        except IndexError:
            video_info = urls[0]

        quality = video_info.get("quality", "unknown")
        kstr = video_info.get("kstr", "")
        jstr = video_info.get("jstr", "")

        final_output = f"{output_base} {quality}.mp4"
        if os.path.exists(final_output):
            await context.bot.edit_message_text("ℹ️ This video was already downloaded", chat_id, message_id)
            return

        video_dec_key_str = decrypt_data(kstr, data_dec_key, iv)
        video_dec_key = base64.b64decode(video_dec_key_str)
        video_m3u8 = decrypt_data(jstr, data_dec_key, iv)
        
        playlist = m3u8.loads(video_m3u8)
        temp_dir = f".temp/{chat_id}_{message_id}"
        
        await context.bot.edit_message_text(f"⏳ Downloading {quality} quality...", chat_id, message_id)
        download_m3u8_playlist(playlist, final_output, video_dec_key, temp_dir)
        
        await context.bot.send_video(
            chat_id=chat_id,
            video=open(final_output, 'rb'),
            caption=f"{os.path.basename(output_base)} ({quality})"
        )
        total_duration = sum(segment.duration for segment in playlist.segments)
        await context.bot.edit_message_text(
            f"⏳ Finalizing video metadata...",
            chat_id,
            message_id
        )

        # Generate thumbnail
        with tempfile.NamedTemporaryFile(suffix=".jpg") as thumb_file:
            thumbnail_path = thumb_file.name
            if generate_thumbnail(final_output, thumbnail_path):
                thumbnail = open(thumbnail_path, 'rb')
            else:
                thumbnail = None

            # Send video with metadata
            with open(final_output, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=f"{os.path.basename(output_base)} ({quality})",
                    duration=int(total_duration),
                    thumb=thumbnail,
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60
                )

        # Cleanup
        shutil.rmtree(temp_dir)
        os.remove(final_output)
        os.remove(html_path)
        
    except Exception as e:
        logger.error(f"Final error: {str(e)}")
        await context.bot.edit_message_text(
            f"❌ Download failed: {str(e)}",
            chat_id,
            message_id
        )
def get_video_duration(file_path):
    """Get video duration using moviepy"""
    try:
        with VideoFileClip(file_path) as video:
            return int(video.duration)
    except Exception as e:
        logger.error(f"Duration detection failed: {str(e)}")
        return 0

def generate_thumbnail(video_path, output_path, time_sec=1):
    """Generate thumbnail using moviepy"""
    try:
        with VideoFileClip(video_path) as clip:
            frame = clip.get_frame(time_sec)
            image = Image.fromarray(frame)
            image.save(output_path)
        return True
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {str(e)}")
        return False
# -------------------- Flask Health Check --------------------
app = Flask(__name__)

@app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8000)

# -------------------- Telegram Bot Configuration --------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_COURSE, SELECTING_SUBJECT, SELECTING_TOPIC, SELECTING_VIDEO , SELECTING_QUALITY = range(5)

# User context keys
USER_STATE = 'user_state'
COURSES = 'courses'
SELECTED_COURSE = 'selected_course'
SELECTED_SUBJECT = 'selected_subject'
SELECTED_TOPIC = 'selected_topic'
SELECTING_QUALITY = 'quality_selected'

# -------------------- Telegram Bot Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome to the Course Download Bot!\n"
        "Use /courses to list available courses."
    )
    return ConversationHandler.END

async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    courses = get_all_purchases()
    if not courses:
        await update.message.reply_text("No courses found.")
        return ConversationHandler.END
    
    context.user_data[COURSES] = courses
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {course['course_name']}", callback_data=str(i))]
        for i, course in enumerate(courses)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select a course:", reply_markup=reply_markup)
    return SELECTING_COURSE

async def course_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    courses = context.user_data[COURSES]
    selected_course = courses[selected_index]
    
    context.user_data[SELECTED_COURSE] = selected_course
    subjects = get_titles(selected_course['id'])
    
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {subj['subject_name']}", callback_data=str(i))]
        for i, subj in enumerate(subjects)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Selected course: {selected_course['course_name']}\nSelect a subject:", reply_markup=reply_markup)
    return SELECTING_SUBJECT

async def subject_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    course = context.user_data[SELECTED_COURSE]
    
    # CORRECTED: Remove the second parameter
    subjects = get_titles(course['id'])  # Only pass course ID
    
    selected_subject = subjects[selected_index]
    context.user_data[SELECTED_SUBJECT] = selected_subject
    
    # Also fix the function name typo (toipic -> topic)
    topics = get_titles_of_topic(course['id'], selected_subject['subjectid'])
    
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {topic['topic_name']}", callback_data=str(i))]
        for i, topic in enumerate(topics)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Selected subject: {selected_subject['subject_name']}\nSelect a topic:", 
        reply_markup=reply_markup
    )
    return SELECTING_TOPIC

async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    course = context.user_data[SELECTED_COURSE]
    subject = context.user_data[SELECTED_SUBJECT]
    
    topics = get_titles_of_topic(course['id'], subject['subjectid'])
    selected_topic = topics[selected_index]
    context.user_data[SELECTED_TOPIC] = selected_topic
    videos = get_all_video_links(course['id'], subject['subjectid'], selected_topic['topicid'])
    
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['Title']}", callback_data=str(i))]
        for i, video in enumerate(videos) if video['material_type'] == "VIDEO"
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Selected topic: {selected_topic['topic_name']}\nSelect a video:", reply_markup=reply_markup)
    return SELECTING_VIDEO

async def video_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_index = int(query.data)
    course = context.user_data[SELECTED_COURSE]
    subject = context.user_data[SELECTED_SUBJECT]
    topic = context.user_data[SELECTED_TOPIC]
    
    videos = get_all_video_links(course['id'], subject['subjectid'], topic['topicid'])
    selected_video = videos[selected_index]
    context.user_data["selected_video"] = selected_video
    
    # Get available qualities
    token = get_video_token(course['id'], selected_video['id'])
    video_html = get_video_html(token)
    context.user_data["video_html"] = video_html
    
    # Get quality options
    qualities = get_available_qualities(video_html)
    
    # Create quality selection keyboard
    keyboard = [
        [InlineKeyboardButton(f"{q.get('quality', 'Unknown')}", callback_data=str(idx))]
        for idx, q in enumerate(qualities)
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Select video quality:",
        reply_markup=reply_markup
    )
    return SELECTING_QUALITY

async def quality_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_quality = int(query.data)
    context.user_data["selected_quality"] = selected_quality
    
    selected_video = context.user_data["selected_video"]
    course = context.user_data[SELECTED_COURSE]
    
    message = await query.edit_message_text("🚀 Starting download...")
    
    # Save HTML temporarily
    os.makedirs('temp', exist_ok=True)
    html_path = f"temp/{selected_video['id']}.html"
    with open(html_path, 'w') as f:
        f.write(context.user_data["video_html"])
    
    output_base = f"temp/{selected_video['Title'].replace(' ', '_')}"
    
    # Start download in background
    await handle_download_start(
        context,
        html_path,
        output_base,
        message.chat_id,
        message.message_id
    )
    
    # Cleanup context data
    keys_to_remove = ["selected_video", "video_html", "selected_quality"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    return ConversationHandler.END

def get_available_qualities(html):
    pattern = r'<script[^>]* id="__NEXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return []
    decoded = json.loads(match.group(1).strip())["props"]["pageProps"]
    return decoded.get("urls", [])
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation"""
    await update.message.reply_text('Operation cancelled.')
    
    # Clear user context data
    context.user_data.clear()
    
    return ConversationHandler.END

def main():
    # Start Flask in a separate thread
    import threading
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Create Telegram Application
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Set up conversation handler
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('courses', list_courses)],
    states={
        SELECTING_COURSE: [CallbackQueryHandler(course_selected)],
        SELECTING_SUBJECT: [CallbackQueryHandler(subject_selected)],
        SELECTING_TOPIC: [CallbackQueryHandler(topic_selected)],
        SELECTING_VIDEO: [CallbackQueryHandler(video_selected)],
        SELECTING_QUALITY: [CallbackQueryHandler(quality_selected)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)
    ],
    allow_reentry=True
)


    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
