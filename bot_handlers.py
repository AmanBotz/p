import os
import re
import json
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from bot import bot, get_all_courses, get_subjects  # Import from your bot.py

# ===== SIMPLE PROGRESS TRACKER =====
class Progress:
    def __init__(self):
        self.steps = {
            'start': "🚀 Starting...",
            'courses': "📚 Loading courses...",
            'subjects': "📖 Fetching subjects...",
            'videos': "🎬 Finding videos..."
        }
    
    async def show(self, message, step):
        """Super simple progress updates"""
        text = self.steps.get(step, "⏳ Processing...")
        await message.edit_text(f"{text}\n\nPlease wait...")

progress = Progress()

# ===== EASY ERROR HANDLING =====
async def safe_delete(message):
    """Delete messages without crashing"""
    try:
        await message.delete()
    except:
        pass

# ===== NOOB-PROOF HANDLERS =====
@bot.on_message(filters.command("courses"))
async def show_courses(client, message):
    """Simple course lister with big buttons"""
    try:
        courses = get_all_courses()
        keyboard = []
        
        # Make big easy-to-press buttons
        for i, course in enumerate(courses[:10], 1):  # Show first 10 only
            keyboard.append([
                InlineKeyboardButton(
                    f"📗 {i}. {course['course_name'][:20]}",
                    callback_data=f"course_{course['id']}"
                )
            ])
        
        # Add cancel button
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])
        
        await message.reply(
            "**Available Courses:**\n(Select with buttons below)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await message.reply(f"😢 Oops! Error: {str(e)[:200]}")

@bot.on_callback_query(filters.regex(r"^course_"))
async def handle_course_select(client, callback):
    """When user clicks a course button"""
    try:
        await progress.show(callback.message, 'subjects')
        course_id = callback.data.split("_")[1]
        subjects = get_subjects(course_id)
        
        keyboard = []
        for i, subject in enumerate(subjects[:10], 1):  # First 10 subjects
            keyboard.append([
                InlineKeyboardButton(
                    f"📘 {i}. {subject['subject_name'][:20]}", 
                    callback_data=f"subject_{course_id}_{subject['subjectid']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back", callback_data="back_to_courses"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])
        
        await callback.edit_message_text(
            "**Available Subjects:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await callback.message.reply(f"😢 Failed: {str(e)[:200]}")
        await safe_delete(callback.message)

@bot.on_callback_query(filters.regex(r"^subject_"))
async def handle_subject_select(client, callback):
    """When user clicks a subject button"""
    try:
        await progress.show(callback.message, 'videos')
        _, course_id, subject_id = callback.data.split("_")
        
        # This would connect to your video listing function
        videos = get_videos(course_id, subject_id)  # Your existing function  # Replace with get_videos(course_id, subject_id)
        
        if not videos:
            await callback.answer("No videos found!", show_alert=True)
            return
            
        keyboard = []
        for i, video in enumerate(videos[:5], 1):  # First 5 videos
            keyboard.append([
                InlineKeyboardButton(
                    f"🎥 {i}. {video['Title'][:20]}",
                    callback_data=f"video_{course_id}_{video['id']}"
                )
            ])
        
        await callback.edit_message_text(
            "**Available Videos:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        await callback.message.reply(f"😢 Error: {str(e)[:200]}")
        await safe_delete(callback.message)

@bot.on_callback_query(filters.regex(r"^(cancel|back)"))
async def handle_actions(client, callback):
    """For back/cancel buttons"""
    try:
        if "cancel" in callback.data:
            await callback.message.reply("❌ Cancelled")
        elif "back" in callback.data:
            await show_courses(client, callback.message)
        
        await safe_delete(callback.message)
    except Exception as e:
        print(f"Action error: {e}")
