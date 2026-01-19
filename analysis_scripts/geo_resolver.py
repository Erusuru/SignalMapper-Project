import re
import pandas as pd
import requests
import time

# ================= CONFIGURATION =================
INPUT_FILE = "map_urls.txt"

# PASTE YOUR COOKIE HERE (Crucial for "Place" links)
MY_COOKIE = "AEC=AaJma5tgCkIirqO5N59VOjhCmhMqaz0z6XuWTm0SfeLd6UwtqwCVtxps9n0; SOCS=CAISHAgCEhJnd3NfMjAyNTA5MjItMF9SQzEaAmJnIAEaBgiA6czGBg; NID=526=Hl2rSX-UvaUJSVfbNw4DFkbzo0cSOPDrL3UTdxKjlao8ZvENrAt7Dki29HT1PlGtvV783-yYBoMloFzQVZc6TFhdJsXrib-GPUHI2MtNIqqCDX8afOTMzW2rGmbzjJ2pKe-wfRJgGSkDcVXst24yzD1_Kp3vHyONO9RVQFKNQbgsC9dpesvn-qXwxKnCcFSqnqd8RKAhrJTZplc42lwJC4GsbsOGQF2LXkGe_Qee1iOamId5mKB48f7EQpi0FaRan9TeW20SVKRtJlSirg6Ub8rruYB9q9SAZNEtiFj7phfw1-D5Nc8WykYgvf1vFNiKdlqpfEMf9-m0RFiumGJp12dKqIzcLxsDdDv-GsVuMiaTJ56ZO9Ahj3iybG3v2nWys_Rs8-5YS4eGdaEwIUfZom-DgSRCyvlEyH-KdegidOVtwphp4x2QwGVCO_ry-S5nlUwqgvXxAY5HE-1Q_MT-NbDdyfqY3CbzPe-7kn1P7q3NzL7vLQGxtHKsDUguo9h8rik8VhnU7C_XkYgLIDn4aWMhOC2eSvJMUxp778Gea75rr_9n0RXcGK4K1PJOlAZbJXVVU8rlAYIMUjbzON2VL7lh7dpUOZ8th6KnMt3_o_r6hRJxgn3_LIwI-XflmSw2fj-3KeUjEud-G37KzCUWY81eN98dWLu1NV5sVsnZxkpZeu_E_KYltg0hMQQB1G805GH4ErJeN3fZAxxIzm1DeFLpokzUbVm-RVMX1LiATTh2X-g9N9BmLnxDgJEqj_0gI9L5rrwGIoBl-Fn-8aLoUnr9_H12C7zlnP-0RVr0lLzi1bnmUneiTEqDi6mx1XdcbbuUtBtHb-6F6rC0Z9ekW7haEjkBo-XCvgXzjGK5Lq1jrLDMQdUjxAbm2VAVppAcdxG_z_2jOxWLft9ShBM37ZU4QIdLLiMwULeFg8G9A1gELBiU35xW9fO6FoKRT4DtTHrVm9S_GZ6kXOsnnypDumyqOc3YpXnsYvV7y6ZVOU5y8KUhui4t0Ov4SYF0-NxOSuNSpvkYbXWBa7BchOe3_z7sgK1exDwKeAvJA1aprdv64z9El-UjXokrHB2CYqM_RFVLIfu5TVZQZKm5-Rvl9WafjhA0u3T07g; SEARCH_SAMESITE=CgQIvp8B; SID=g.a0003wixEV5BR2--uSJ3YXRjmk0MkvlCMDLb36RhAbs_sabz_UCS7RLmvqr5hSA-bLmU7pa5xQACgYKAXkSARMSFQHGX2MiztQed4bTiQtEJcEkzezE-xoVAUF8yKqpkE10AzFfvtLyMPZFwFVz0076; __Secure-1PSID=g.a0003wixEV5BR2--uSJ3YXRjmk0MkvlCMDLb36RhAbs_sabz_UCSWZQipPYCz_eCSQ3YKHlAzAACgYKAcwSARMSFQHGX2MifwPxguwjcQ7RsRISJpGTvxoVAUF8yKpc8rIRkN-2m1l9IDUi1yfv0076; __Secure-3PSID=g.a0003wixEV5BR2--uSJ3YXRjmk0MkvlCMDLb36RhAbs_sabz_UCSxP2goK-nWlwpXPPOhBrmmQACgYKAesSARMSFQHGX2MiJyeZ84rwLkIvzvOEn2C2ahoVAUF8yKrZahtJDcVLaVXuAY-ckg2q0076; HSID=AAcXMd-xo-OAFB-j4; SSID=Aqs7HUojFGcbV0qa0; APISID=q4kaontcNO_huw9p/AfatFxzaSOCs0soAn; SAPISID=MZ0l1zjDkwpVU3xe/A_vs2DnTFpz0OQyRl; __Secure-1PAPISID=MZ0l1zjDkwpVU3xe/A_vs2DnTFpz0OQyRl; __Secure-3PAPISID=MZ0l1zjDkwpVU3xe/A_vs2DnTFpz0OQyRl; SIDCC=AKEyXzW0RV9styEwoCoGmFMaH8I2X1bgPmpNXqHAcVGy0b6badMgJJBxT-sVGXdvGxmz62TzoQ; __Secure-1PSIDCC=AKEyXzVxPue3FoRaWjS4XoSU1os3bRDPaWP2dg31IZB_N3LHu9Bbad00LrSSvXNslEmT_MVj2Mg; __Secure-3PSIDCC=AKEyXzV_zf4qZ1B7JrJKfGqW0JYPfVVlW40T9p3ZzRj656IzReHwtc9oNqm_n0RPtxBAX1ERK7A; __Secure-1PSIDTS=sidts-CjIBwQ9iI4ryrkUnCX91RAL1VhMD_Pvqx3qoFwmwlmTon4MStYktRQ9VOCcKUM0Tg7OG8RAA; __Secure-3PSIDTS=sidts-CjIBwQ9iI4ryrkUnCX91RAL1VhMD_Pvqx3qoFwmwlmTon4MStYktRQ9VOCcKUM0Tg7OG8RAA; __Secure-STRP=ADq1D7ppYjbAJ-uj57Y6AnggdspBjEkGBszvbAtGi8MLammfV3OPEXFI6w676fUHBxHyFZ4imMGsMk6axyYzGM5pv2HHPhAlww"
# =================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": MY_COOKIE,
    "Accept-Language": "en-US,en;q=0.9"
}

data = []

print(f"Reading {INPUT_FILE}...")
try:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
except FileNotFoundError:
    print("Error: map_urls.txt not found.")
    exit()

print(f"Processing {len(lines)} items (Downloading HTML content)...")
print("This will take about 2-3 minutes.")

for i, line in enumerate(lines):
    if not line.strip(): continue

    # Calculate ID (186 down to 1)
    current_id = 186 - i
    
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
            # Pattern: [42.12345, 23.12345]
            # We look for numbers that match Blagoevgrad coordinates (Lat 41-43, Lon 22-24)
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
                    print(f"❌ ID {current_id}: No coords in HTML.")

            time.sleep(0.5) # Wait 0.5 seconds to not crash Google
            
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
    df.to_csv("map_coordinates_RESOLVED.csv", index=False)
    print("\nSUCCESS! Saved to 'map_coordinates_RESOLVED.csv'")
else:
    print("No data extracted.")
