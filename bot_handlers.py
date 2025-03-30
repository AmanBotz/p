import os
import re
import json
import time
import base64
import hashlib
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from Crypto.Cipher import AES
from base64 import b64decode
import m3u8
from concurrent.futures import ThreadPoolExecutor

# ===== PROGRESS MANAGER =====
class ProgressManager:
    def __init__(self):
        self.last_update = 0
        self.message = None
    
    async def update(self, text, message=None, force=False):
        """Smart progress updater with rate limiting"""
        if message:
            self.message = message
            
        now = time.time()
        if force or (now - self.last_update) > 5:  # 5-second throttle
            try:
                if len(text) > 4000:
                    text = text[:3900] + "…[truncated]"
                await self.message.edit_text(text)
                self.last_update = now
            except Exception:
                pass

progress = ProgressManager()
user_data = {}

# ===== HELPER FUNCTIONS =====
def human_size(size):
    """Convert bytes to human-readable format"""
    units = ['B', 'KB', 'MB', 'GB']
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

def clean_filename(name):
    """Make safe filenames"""
    return re.sub(r'[\\/*?:"<>|]', "", name)[:50]

# ===== DOWNLOAD CORE =====
def decrypt_stream(enc_data, key, iv):
    """AES-CBC decryption"""
    cipher = AES.new(b64decode(key), AES.MODE_CBC, b64decode(iv))
    return unpad(cipher.decrypt(b64decode(enc_data)), AES.block_size).decode()

def download_segment(url, key, iv, path):
    """Download and decrypt a single segment"""
    try:
        seg = requests.get(url, timeout=15).content
        cipher = AES.new(key, AES.MODE_CBC, iv)
        with open(path, "wb") as f:
            f.write(cipher.decrypt(seg))
        return True
    except Exception:
        return False

def download_video(m3u8_url, key, iv, user_id, quality):
    """Main download function"""
    temp_dir = f"temp_{user_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    playlist = m3u8.load(m3u8_url)
    total = len(playlist.segments)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i, seg in enumerate(playlist.segments):
            path = f"{temp_dir}/seg_{i}.ts"
            futures.append(executor.submit(
                download_segment,
                seg.uri, key, iv, path
            ))
            
        for i, future in enumerate(futures):
            future.result()
            if i % 5 == 0:  # Update every 5 segments
                await progress.update(
                    f"⬇️ Downloading {quality}…\n"
                    f"Progress: {i+1}/{total} segments\n"
                    f"({((i+1)/total)*100:.1f}%)"
                )
    
    # Combine segments
    output = f"video_{user_id}.mp4"
    with open(output, "wb") as out:
        for i in range(total):
            try:
                with open(f"{temp_dir}/seg_{i}.ts", "rb") as f:
                    out.write(f.read())
                os.remove(f"{temp_dir}/seg_{i}.ts")
            except Exception:
                continue
                
    os.rmdir(temp_dir)
    return output

# ===== BOT HANDLERS =====
@bot.on_callback_query(filters.regex(r"^quality_"))
async def handle_quality(client, callback: CallbackQuery):
    try:
        _, cid, vid, quality = callback.data.split("_")
        user_id = callback.from_user.id
        
        await progress.update(
            f"⏳ Preparing {quality} quality…",
            callback.message,
            force=True
        )
        
        # Store download info
        user_data[user_id] = {
            "cid": cid,
            "vid": vid,
            "quality": quality,
            "message": callback.message
        }
        
        await start_download(client, user_id)
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Error: {str(e)[:3000]}")

async def start_download(client, user_id):
    data = user_data.get(user_id)
    if not data:
        return
    
    try:
        # 1. Get video token
        await progress.update("🔍 Getting video info…", data["message"])
        token = get_video_token(data["cid"], data["vid"])
        html = get_video_html(token)
        
        # 2. Extract stream data
        await progress.update("🔐 Decrypting…", data["message"])
        page_data = json.loads(re.search(
            r'<script id="__NEXT_DATA__".*?>(.*?)</script>', html
        ).group(1))
        props = page_data["props"]["pageProps"]
        
        # 3. Prepare decryption
        key = get_decryption_key(props["datetime"], props["token"])
        iv = props["ivb6"]
        stream = next(
            (q for q in props["urls"] if q["quality"] == data["quality"]),
            None
        )
        if not stream:
            raise Exception("Quality not available")
        
        # 4. Download
        video_path = download_video(
            decrypt_stream(stream["jstr"], key, iv),
            b64decode(decrypt_stream(stream["kstr"], key, iv)),
            b64decode(iv),
            user_id,
            data["quality"]
        )
        
        # 5. Upload
        await progress.update("📤 Uploading…", data["message"])
        await client.send_video(
            chat_id=user_id,
            video=video_path,
            caption=f"🎬 {data['quality']} Quality",
            progress=upload_progress,
            progress_args=(data['message'],)
        )
        
        await data['message'].delete()
        
    except Exception as e:
        await data['message'].edit_text(f"❌ Failed: {str(e)[:3000]}")
    finally:
        # Cleanup
        if user_id in user_data:
            del user_data[user_id]
        for file in [f"video_{user_id}.mp4", f"temp_{user_id}"]:
            try:
                if os.path.exists(file):
                    if os.path.isdir(file):
                        os.rmdir(file)
                    else:
                        os.remove(file)
            except Exception:
                pass

async def upload_progress(current, total, message):
    """Handle upload progress with throttling"""
    percent = (current / total) * 100
    if percent % 10 == 0:  # Update every 10%
        await progress.update(
            f"📤 Uploading…\n"
            f"Progress: {percent:.1f}%\n"
            f"{human_size(current)} / {human_size(total)}",
            message
        )
