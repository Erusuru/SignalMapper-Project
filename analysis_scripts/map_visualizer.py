import os
import time
from playwright.sync_api import sync_playwright

# ===========================
# ⚙️ CONFIGURATION
# ===========================
HTML_FILE = "A1.html" 
OUTPUT_IMAGE = "Blagoevgrad_Ultra.png"

# Window Size (Keep small for speed)
NAV_WIDTH = 1200
NAV_HEIGHT = 900

# Quality Boost (3 = 4K resolution on small screen)
PIXEL_RATIO = 3 

def render():
    if not os.path.exists(HTML_FILE):
        print(f"❌ Error: {HTML_FILE} not found.")
        return

    file_path = f"file://{os.path.abspath(HTML_FILE)}"
    
    print(f"🚀 Initializing Renderer...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--use-gl=desktop',
                '--enable-webgl',
                '--ignore-gpu-blocklist',
                f'--window-size={NAV_WIDTH},{NAV_HEIGHT}'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': NAV_WIDTH, 'height': NAV_HEIGHT},
            device_scale_factor=1
        )
        page = context.new_page()
        
        print(f"📂 Opening map...")
        page.goto(file_path)

        # -------------------------------------------------
        # PHASE 1: POSITIONING
        # -------------------------------------------------
        print("\n" + "="*50)
        print("📍 PHASE 1: POSITIONING")
        print("   1. Move to Blagoevgrad.")
        print("   2. Set your angle.")
        print("   3. DO NOT resize the window.")
        print("="*50 + "\n")
        
        input("👉 PRESS [ENTER] TO BOOST RESOLUTION...")
        
        # -------------------------------------------------
        # PHASE 2: RETINA BOOST & LOAD
        # -------------------------------------------------
        print(f"\n⚡ Boosting Quality to {PIXEL_RATIO}x...")
        
        # Boost Density
        client = page.context.new_cdp_session(page)
        client.send("Emulation.setDeviceMetricsOverride", {
            "width": NAV_WIDTH,
            "height": NAV_HEIGHT,
            "deviceScaleFactor": PIXEL_RATIO,
            "mobile": False
        })
        
        print("⏳ Waiting 20 seconds for GPU to catch up...")
        time.sleep(20)
        
        # -------------------------------------------------
        # PHASE 3: VISUAL CHECK (The Fix)
        # -------------------------------------------------
        print("\n" + "="*50)
        print("👀 PHASE 3: VISUAL CHECK")
        print("   Look at the browser window.")
        print("   - Are the streets sharp?")
        print("   - ARE THE COLORED DOTS VISIBLE?")
        print("   If no dots: Wait longer. Don't press Enter yet.")
        print("   If dots are there: Press Enter.")
        print("="*50 + "\n")
        
        input("👉 PRESS [ENTER] TO TAKE PHOTO NOW...")

        # Hide UI
        print("🧹 Cleaning UI...")
        page.add_style_tag(content="""
            .side-panel, .map-control, .bottom-widget, .mapboxgl-ctrl 
            { display: none !important; }
        """)
        
        # Capture
        print("📸 Snapping Screenshot...")
        page.screenshot(path=OUTPUT_IMAGE)
        
        browser.close()
        print(f"✅ DONE! Saved high-quality map to: {OUTPUT_IMAGE}")

if __name__ == "__main__":
    render()
