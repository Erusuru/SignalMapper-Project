import os
import re
import pandas as pd
import pytesseract
from PIL import Image, ImageOps
import sys

# Regex Patterns
RSRP_PATTERN = r"RSRP:(-?\d+)"
SNR_PATTERN = r"SNR:(\d+\.?\d*)"

def process_images(folder_path):
    data = []
    
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder '{folder_path}' not found.")
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files.sort()

    print(f"🔍 Found {len(files)} images. Starting OCR...")

    for index, filename in enumerate(files, start=1):
        try:
            img_path = os.path.join(folder_path, filename)
            img = Image.open(img_path)
            
            # Optimization Pipeline
            img = ImageOps.invert(img.convert('RGB')) # Invert
            img = img.convert('L') # Grayscale
            img = img.point(lambda x: 0 if x < 150 else 255) # Threshold

            # OCR
            text = pytesseract.image_to_string(img, config='--psm 6')
            
            rsrp = re.search(RSRP_PATTERN, text)
            snr = re.search(SNR_PATTERN, text)
            
            rsrp_val = rsrp.group(1) if rsrp else "N/A"
            snr_val = snr.group(1) if snr else "N/A"
            
            status = "✅" if (rsrp_val != "N/A") else "⚠️"
            print(f"[{index}] {status} {filename} -> RSRP: {rsrp_val} | SNR: {snr_val}")
            
            data.append({
                "ID": index,
                "Filename": filename,
                "RSRP": rsrp_val,
                "SNR": snr_val
            })

        except Exception as e:
            print(f"❌ Error on {filename}: {e}")

    if data:
        df = pd.DataFrame(data)
        df.to_csv("ocr_results.csv", index=False)
        print(f"\n🎉 Done! Results saved to 'ocr_results.csv'")
    else:
        print("No data extracted.")

if __name__ == "__main__":
    print("--- Android ServiceMode OCR Tool ---")
    target_folder = input("Enter path to folder containing screenshots: ").strip()
    # Remove quotes if user copied path as "C:\Path"
    target_folder = target_folder.replace('"', '').replace("'", "")
    process_images(target_folder)