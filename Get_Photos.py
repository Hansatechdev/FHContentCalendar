import json
import os
import pandas as pd
import requests
from datetime import datetime

# === CONFIGURATION ===
EXCEL_FILE = 'Content_Calendar.xlsx'          # Your Excel file name
SHEET_NAME = 'Feed List'                      # Sheet name (change if different)
JSON_FILE = 'dataset_facebook-posts-scraper_2025-11-18_14-57-30-605.json'

SAVE_FOLDER = 'downloaded_images'
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Column name for Original FB Post URL (exact header)
POST_URL_COL_NAME = 'Original FB Post URL'    # Updated to match your header

# Column name for date
DATE_COL_NAME = 'Publish Date (DD/MM/YYYY)'   # Exact header name for the date column

# === Load Excel to get post_url -> date mapping ===
print("Loading Excel file...")
df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)

# Verify columns
print("Excel columns found:", df.columns.tolist())

if POST_URL_COL_NAME not in df.columns:
    raise ValueError(f"Column '{POST_URL_COL_NAME}' not found in Excel!")
if DATE_COL_NAME not in df.columns:
    raise ValueError(f"Column '{DATE_COL_NAME}' not found in Excel!")

# Create mapping: post_url -> raw_date (only rows with both filled)
date_map = {}
for idx, row in df.iterrows():
    post_url = row[POST_URL_COL_NAME]
    raw_date = row[DATE_COL_NAME]
    
    if pd.notna(post_url) and pd.notna(raw_date):
        post_url = str(post_url).strip()
        if post_url:  # Ensure not empty
            date_map[post_url] = raw_date

print(f"Loaded {len(date_map)} post-to-date mappings from Excel.")

if len(date_map) == 0:
    print("WARNING: No valid mappings found. Check that column 'Original FB Post URL' has full URLs like 'https://www.facebook.com/foodforthehungry/posts/pfbid...'")

# === Load JSON posts ===
print("Loading JSON posts...")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    posts = json.load(f)

# Build reverse lookup: url -> post data
post_data_by_url = {post.get('url', '').strip(): post for post in posts}

print(f"JSON contains {len(post_data_by_url)} unique post URLs.")

# === Download loop ===
downloaded_count = 0
skipped_no_match = 0
for post_url, raw_date in date_map.items():
    if post_url not in post_data_by_url:
        print(f"Skipping (no match in JSON): {post_url}")
        skipped_no_match += 1
        continue

    # Normalize date to YYYY-MM-DD
    try:
        if isinstance(raw_date, (pd.Timestamp, datetime)):
            dt = raw_date.date()
        else:
            # Handle string formats
            raw_str = str(raw_date).strip()
            # Try DD/MM/YYYY first
            try:
                dt = datetime.strptime(raw_str, '%d/%m/%Y').date()
            except ValueError:
                # Fallback to YYYY-MM-DD or other
                dt = pd.to_datetime(raw_str).date()
        
        filename = dt.strftime('%Y-%m-%d') + '.jpg'
        filepath = os.path.join(SAVE_FOLDER, filename)
        
        if os.path.exists(filepath):
            print(f"Skipping (already exists): {filename}")
            continue
    except Exception as e:
        print(f"Invalid date for {post_url}: {raw_date} -> {e}")
        continue

    post = post_data_by_url[post_url]
    
    # Extract primary image URL
    image_url = None
    media = post.get('media', [])
    for m in media:
        if m.get('__typename') == 'Photo':
            photo_image = m.get('photo_image') or m.get('image', {})
            image_url = photo_image.get('uri')
            if image_url:
                break
    
    # Fallback to thumbnail
    if not image_url:
        for m in media:
            if 'thumbnail' in m:
                image_url = m['thumbnail']
                break
    
    if not image_url:
        print(f"No image found for post: {post_url}")
        continue
        
    # Download image with Facebook referer to avoid 403
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36',
            'Referer': 'https://www.facebook.com/'  # Key fix for 403
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as img_file:
            img_file.write(response.content)
        
        print(f"Downloaded: {filename} <- {post_url}")
        downloaded_count += 1
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            print(f"403 Forbidden (signature expired/blocked): {image_url} — Download manually from post")
        else:
            print(f"HTTP error downloading {image_url}: {http_err}")
    except Exception as e:
        print(f"Error downloading {image_url}: {e}")

print(f"\nDownload complete! {downloaded_count} images saved.")
if skipped_no_match > 0:
    print(f"{skipped_no_match} posts skipped due to no match in JSON (check URL spelling/case).")