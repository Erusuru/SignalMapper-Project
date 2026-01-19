import re
import pandas as pd
import requests
import time
import os

# ================= CONFIGURATION =================
# We now ask the user for these inputs instead of hardcoding
# =================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def resolve_locations():
    print("--- Google Maps Location Resolver ---")
    
    # 1. Get Input File
    input_file = input("Enter the filename (e.g., map_urls.txt): ").strip().replace('"', '')
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found.")
        return

    # 2. Get Cookie (Securely)
    print("\n[Optional] Paste your Google Maps Cookie to resolve 'Place' links.")
    print("If you skip this, some links might fail.")
    my_cookie = input("Cookie (Press Enter to skip): ").strip()
    
    if my_cookie:
        HEADERS["Cookie"] = my_cookie

    data = []

    print(f"\nReading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Processing {len(lines)} items...")
    print("This may take a few minutes...")

    for i, line in enumerate(lines):
        if not line.strip(): continue

        # Calculate ID (assuming reverse order 186 -> 1, optional logic)
        current_id = len(lines) - i 
        
        # Extract URL
        url_match = re.search(r'(https?://[^\s]+)', line)
        if not url_match: continue
        url = url_match.group(1)

        lat, lon = None, None

        # --- METHOD A: Direct Search URL (Fast) ---
        match_search = re.search(r'search/(\d+\.\d+),(\d+\.\d+)', url)
        if match_search:
            lat = float(match_search.group(1))
            lon = float(match_search.group(2))
            print(f"✅ ID {current_id}: Direct -> {lat}, {lon}")

        # --- METHOD B: Place URL (Download Content) ---
        else:
            try:
                # Download the page content
                response = requests.get(url, headers=HEADERS, timeout=10)
                html_content = response.text
                
                # 1. Try to find the "center" of the view in HTML
                match_content = re.search(r'\[\s*(4[12]\.\d+)\s*,\s*(2[234]\.\d+)\s*\]', html_content)
                
                if match_content:
                    lat = float(match_content.group(1))
                    lon = float(match_content.group(2))
                    print(f"✅ ID {current_id}: Found in HTML -> {lat}, {lon}")
                else:
                    # 2. Try to find the URL inside the HTML meta tags
                    match_meta = re.search(r'content=".*?center=(\d+\.\d+)%2C(\d+\.\d+)', html_content)
                    if match_meta:
                        lat = float(match_meta.group(1))
                        lon = float(match_meta.group(2))
                        print(f"✅ ID {current_id}: Found in Meta -> {lat}, {lon}")
                    else:
                        print(f"❌ ID {current_id}: No coords found. (Cookie might be expired?)")

                time.sleep(0.5) # Wait to be polite
                
            except Exception as e:
                print(f"❌ ID {current_id}: Network Error {e}")

        # Save
        if lat and lon:
            data.append({
                "ID": current_id,
                "Latitude": lat,
                "Longitude": lon
            })

    # --- SAVE ---
    if data:
        df = pd.DataFrame(data)
        df = df.sort_values(by="ID")
        output_name = "resolved_coordinates.csv"
        df.to_csv(output_name, index=False)
        print(f"\n🎉 SUCCESS! Saved to '{output_name}'")
    else:
        print("No data extracted.")

if __name__ == "__main__":
    resolve_locations()
