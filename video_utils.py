import os
import re
import base64
import hashlib
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from concurrent.futures import ThreadPoolExecutor
import cv2
import subprocess
from typing import Optional

# ===== CORE DECRYPTION =====
def get_decryption_key(time_val: str, token: str) -> str:
    """Generate AES key from timestamp and token"""
    try:
        n = time_val[-4:]
        r = int(n[0])
        i = int(n[1:3])
        o = int(n[3])
        combined = time_val + token[r:r+i]
        sha = hashlib.sha256(combined.encode()).digest()
        
        if o == 6:
            key = sha[:16]
        elif o == 7:
            key = sha[:24]
        else:
            key = sha
            
        return base64.b64encode(key).decode()
    except Exception as e:
        print(f"Key generation failed: {str(e)}")
        return ""

def decrypt_data(enc_data: str, key: str, iv: str) -> str:
    """AES-CBC decryption with error handling"""
    try:
        cipher = AES.new(
            base64.b64decode(key),
            AES.MODE_CBC,
            base64.b64decode(iv)
        )
        decrypted = cipher.decrypt(base64.b64decode(enc_data))
        return unpad(decrypted, AES.block_size).decode()
    except Exception as e:
        print(f"Decryption failed: {str(e)}")
        return ""

# ===== VIDEO DOWNLOAD =====
def decode_segment(data: str, ext: str) -> bytes:
    """Handle different encoded formats"""
    decoders = {
        "tsa": lambda d: base64.b64decode(''.join([chr(ord(c) - 0x14) for c in d])),
        "tsb": lambda d: base64.b64decode(''.join([chr((ord(c) >> 0x3) ^ 0x2A) for c in d])),
        "tsc": lambda d: base64.b64decode(''.join([chr(ord(c) - 0xA) for c in d])),
        "tsd": lambda d: base64.b64decode(''.join([chr(ord(c) >> 0x2) for c in d])),
        "tse": lambda d: base64.b64decode(''.join([chr((ord(c) ^ 0x2A) >> 0x3) for c in d]))
    }
    return decoders.get(ext, lambda x: x)(data)

def download_segment(url: str, key: bytes, iv: bytes, output_path: str) -> bool:
    """Download and decrypt a single video segment"""
    for _ in range(3):  # 3 retries
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Get file extension and decode
            ext = url.split('.')[-1]
            decoded = decode_segment(response.text, ext)
            
            # Decrypt with AES
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(decoded)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            return True
        except Exception as e:
            print(f"Segment failed: {url} - {str(e)}")
    return False

def download_video_stream(m3u8_url: str, key: bytes, iv: bytes, output_file: str) -> bool:
    """Download entire video stream"""
    try:
        playlist = requests.get(m3u8_url).text
        segments = [line.split()[-1] for line in playlist.split('\n') if line.startswith('http')]
        
        temp_dir = f"temp_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Parallel download with progress
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, seg_url in enumerate(segments):
                futures.append(executor.submit(
                    download_segment,
                    seg_url,
                    key,
                    iv,
                    f"{temp_dir}/seg_{i:04d}.ts"
                ))
            
            # Wait for completion
            [f.result() for f in futures]
        
        # Merge segments
        with open(output_file, 'wb') as outfile:
            for i in range(len(segments)):
                try:
                    with open(f"{temp_dir}/seg_{i:04d}.ts", 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(f"{temp_dir}/seg_{i:04d}.ts")
                except FileNotFoundError:
                    continue
                    
        os.rmdir(temp_dir)
        return True
    except Exception as e:
        print(f"Download failed: {str(e)}")
        return False

# ===== VIDEO PROCESSING =====
def extract_thumbnail(video_path: str, output_path: str) -> bool:
    """Extract first frame as thumbnail"""
    try:
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            cv2.imwrite(output_path, frame)
        return success
    except Exception as e:
        print(f"Thumbnail failed: {str(e)}")
        return False

def convert_to_mp4(input_path: str, output_path: str) -> bool:
    """Convert to standard MP4 format"""
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac', '-movflags', '+faststart',
            output_path
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed: {str(e)}")
        return False
