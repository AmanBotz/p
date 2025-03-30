import os
import re
import subprocess
import cv2
import requests
from Crypto.Cipher import AES
from base64 import b64decode
import m3u8
from concurrent.futures import ThreadPoolExecutor

def sanitize_filename(name):
    """Remove invalid filesystem characters"""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_decryption_key(time_val, token):
    """Generate AES key from timestamp and token"""
    n = time_val[-4:]
    r, i, o = int(n[0]), int(n[1:3]), int(n[3])
    a = time_val + token[r:i]
    
    s = hashlib.sha256(a.encode()).digest()
    key = s[:16] if o == 6 else (s[:24] if o == 7 else s)
    return base64.b64encode(key).decode()

def decrypt_data(enc_data, key, iv):
    """AES-CBC decryption"""
    cipher = AES.new(b64decode(key), AES.MODE_CBC, b64decode(iv))
    return unpad(cipher.decrypt(b64decode(enc_data)), AES.block_size).decode()

def download_segment(segment_url, key, iv, output_path):
    """Download and decrypt a single video segment"""
    try:
        segment = requests.get(segment_url, timeout=15).content
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(segment)
        
        with open(output_path, "wb") as f:
            f.write(decrypted)
        return True
    except Exception as e:
        print(f"Segment download failed: {str(e)}")
        return False

def download_video_stream(m3u8_url, key, iv, output_path, quality, max_workers=5):
    """Download video stream with quality selection"""
    playlist = m3u8.load(m3u8_url)
    temp_dir = f".temp_{quality}"
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Downloading {len(playlist.segments)} segments...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, segment in enumerate(playlist.segments):
            futures.append(
                executor.submit(
                    download_segment,
                    segment.uri,
                    key,
                    iv,
                    f"{temp_dir}/seg_{i}.ts"
                )
            )
        
        for future in futures:
            future.result()

    # Combine segments
    with open(output_path, "wb") as out:
        for i in range(len(playlist.segments)):
            try:
                with open(f"{temp_dir}/seg_{i}.ts", "rb") as seg:
                    out.write(seg.read())
                os.remove(f"{temp_dir}/seg_{i}.ts")
            except FileNotFoundError:
                continue
    
    os.rmdir(temp_dir)
    return output_path

def extract_thumbnail(video_path, output_path):
    """Extract first frame as thumbnail using OpenCV"""
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    if success:
        cv2.imwrite(output_path, image)
    return success

def convert_to_mp4(input_path, output_path):
    """Convert video to standard MP4 format"""
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path
