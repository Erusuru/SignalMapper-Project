import os
import time
from playwright.sync_api import sync_playwright

# Window Size (Keep small for speed)
NAV_WIDTH = 1200
NAV_HEIGHT = 900

# Quality Boost (3 = 4K resolution on small screen)
PIXEL_RATIO = 3 

def render():
    print("--- Kepler.gl High-Res Screenshot Tool ---")
    html_file = input("Enter the HTML map filename (e.g. map.html): ").strip().replace('"', '')
    
    if not os.path.exists(html_file):
        print(f"❌ Error: {html_file} not found.")
        return

    output_image = html_file.replace(".html", "_4k.png")
    file_path = f"file://{os.path.abspath(html_file)}"
    
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
        print("   1. Move the map to your desired view.")
        print("   2. Set your angle/tilt.")
        print("   3. DO NOT resize the window manually.")
        print("="*50 + "\n")
        
        input("👉 PRESS [ENTER] WHEN READY TO BOOST RESOLUTION...")
        
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
        
        print("⏳ Waiting 15 seconds for WebGL to re-render...")
        time.sleep(15)
        
        # -------------------------------------------------
        # PHASE 3: VISUAL CHECK
        # -------------------------------------------------
        print("\n" + "="*50)
        print("👀 PHASE 3: VISUAL CHECK")
        print("   Look at the browser window.")
        print("   - Are the streets sharp?")
        print("   - ARE THE COLORED DOTS VISIBLE?")
        print("="*50 + "\n")
        
        input("👉 PRESS [ENTER] TO TAKE PHOTO NOW...")

        # Hide UI elements commonly found in Kepler.gl exports
        print("🧹 Cleaning UI...")
        page.add_style_tag(content="""
            .side-panel, .map-control, .bottom-widget, .mapboxgl-ctrl 
            { display: none !important; }
        """)
        
        # Capture
        print(f"📸 Snapping Screenshot to {output_image}...")
        page.screenshot(path=output_image)
        
        browser.close()
        print(f"✅ DONE! Saved.")

if __name__ == "__main__":
    render()
