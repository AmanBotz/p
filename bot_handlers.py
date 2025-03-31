from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import bot, get_all_courses, get_subjects, get_topics, get_video_token
import time

# ===== PROGRESS TRACKER =====
class ProgressTracker:
    def __init__(self):
        self.last_update = 0
        
    async def update(self, message, text):
        """Rate-limited progress updates"""
        if time.time() - self.last_update > 5:  # 5-second throttle
            await message.edit_text(text[:4000])  # Truncate if too long
            self.last_update = time.time()

progress = ProgressTracker()

# ===== HELPER FUNCTIONS =====
async def safe_edit(message, text, buttons=None):
    """Crash-proof message editing"""
    try:
        await message.edit_text(
            text=text,
            reply_markup=buttons
        )
    except Exception:
        pass

# ===== BOT COMMANDS =====        
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    await message.reply(
        "📚 **Parmar Academy Video Bot**\n\n"
        "Use /courses to browse available content\n"
        "Use /cancel to stop any operation"
    )

@bot.on_message(filters.command("courses"))
async def show_courses(client, message):
    courses = get_all_courses()
    if not courses:
        await message.reply("❌ No courses available currently")
        return

    keyboard = []
    for idx, course in enumerate(courses[:10], 1):  # Limit to 10 courses
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {course['course_name'][:30]}",
                callback_data=f"course_{course['id']}"
            )
        ])
        
    await message.reply(
        "**Available Courses:**\nSelect one:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== CALLBACK HANDLERS =====
@bot.on_callback_query(filters.regex(r"^course_"))
async def handle_course(client, callback):
    course_id = callback.data.split("_")[1]
    subjects = get_subjects(course_id)
    
    if not subjects:
        await callback.answer("No subjects found!", show_alert=True)
        return

    keyboard = []
    for idx, subject in enumerate(subjects[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {subject['subject_name'][:30]}", 
                callback_data=f"subject_{course_id}_{subject['subjectid']}"
            )
        ])
        
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_courses")])
    
    await safe_edit(
        callback.message,
        "**Available Subjects:**\nSelect one:",
        InlineKeyboardMarkup(keyboard)
    )

@bot.on_callback_query(filters.regex(r"^subject_"))
async def handle_subject(client, callback):
    _, course_id, subject_id = callback.data.split("_")
    topics = get_topics(course_id, subject_id)
    
    if not topics:
        await callback.answer("No topics found!", show_alert=True)
        return

    keyboard = []
    for idx, topic in enumerate(topics[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {topic['topic_name'][:30]}",
                callback_data=f"topic_{course_id}_{subject_id}_{topic['topicid']}"
            )
        ])
        
    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data=f"back_subjects_{course_id}")
    ])
    
    await safe_edit(
        callback.message,
        "**Available Topics:**\nSelect one:",
        InlineKeyboardMarkup(keyboard)
    )

@bot.on_callback_query(filters.regex(r"^back_"))
async def handle_back(client, callback):
    data = callback.data.split("_")
    
    if data[1] == "courses":
        await show_courses(client, callback.message)
    elif data[1] == "subjects":
        course_id = data[2]
        subjects = get_subjects(course_id)
        
        keyboard = []
        for idx, subject in enumerate(subjects[:10], 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"{idx}. {subject['subject_name'][:30]}",
                    callback_data=f"subject_{course_id}_{subject['subjectid']}"
                )
            ])
            
        await safe_edit(
            callback.message,
            "**Available Subjects:**\nSelect one:",
            InlineKeyboardMarkup(keyboard)
        )

@bot.on_callback_query(filters.regex(r"^topic_"))
async def handle_topic(client, callback):
    _, course_id, subject_id, topic_id = callback.data.split("_")
    
    # Get actual videos list
    videos = get_videos(course_id, subject_id, topic_id)
    
    if not videos:
        await callback.answer("❌ No videos available", show_alert=True)
        return

    keyboard = []
    for idx, video in enumerate(videos[:10], 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {video['title'][:30]}",
                callback_data=f"video_{course_id}_{video['video_id']}"  # Use video_id here
            )
        ])
        
    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data=f"back_topics_{course_id}_{subject_id}")
    ])
    
    await safe_edit(
        callback.message,
        "**Available Videos:**\nSelect one:",
        InlineKeyboardMarkup(keyboard)
    )

@bot.on_callback_query(filters.regex(r"^video_"))
async def handle_video_selection(client, callback):
    _, course_id, video_id = callback.data.split("_")
    
    token = get_video_token(course_id, video_id)
    
    if not token:
        await callback.answer("❌ Video unavailable", show_alert=True)
        return
        
    # Rest of your download logic
        
    await callback.answer("✅ Download starting...", show_alert=False)
    await progress.update(callback.message, "⏳ Preparing video download...")
