import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# GPS Rounding (~11 meters precision)
GEO_PRECISION = 4 

def clean_and_load(filepath, label, target_operator=None):
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(filepath)
        # Standardize Columns
        df.columns = [c.capitalize() for c in df.columns]
        rename_map = {'Latitude': 'lat', 'Longitude': 'lon', 'Rsrp': 'rsrp', 'Snr': 'snr', 'Operator': 'operator'}
        df = df.rename(columns=rename_map)
        
        # Numeric Cleaning
        df['rsrp'] = pd.to_numeric(df['rsrp'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon', 'rsrp'])

        # --- OPERATOR FILTERING ---
        if target_operator and 'operator' in df.columns:
            mask = df['operator'].astype(str).str.contains(target_operator, case=False, na=False)
            df = df[mask]
        
        print(f"✅ Loaded {label}: {len(df)} points" + (f" (Filtered for '{target_operator}')" if target_operator else ""))
        return df[['lat', 'lon', 'rsrp']]
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return pd.DataFrame()

def match_locations(dfs):
    """ Matches points where ALL phones were present """
    print("\n🔄 Matching GPS locations across devices...")
    
    # Round coordinates for grid matching
    for i, df in enumerate(dfs):
        df['grid_lat'] = df['lat'].round(GEO_PRECISION)
        df['grid_lon'] = df['lon'].round(GEO_PRECISION)
        # Aggregate duplicates in same grid
        dfs[i] = df.groupby(['grid_lat', 'grid_lon'])['rsrp'].mean().reset_index().rename(columns={'rsrp': f'rsrp_{i}'})

    # Start merging
    merged = dfs[0]
    for i in range(1, len(dfs)):
        merged = pd.merge(merged, dfs[i], on=['grid_lat', 'grid_lon'], how='inner')
    
    return merged

def generate_battle_report(merged, labels):
    print("\n" + "="*60)
    print(f"🤖 HARDWARE BATTLE: {labels[0]} vs {labels[1]}")
    print("="*60)
    
    merged['diff'] = merged['rsrp_0'] - merged['rsrp_1']
    
    total_spots = len(merged)
    dev0_wins = len(merged[merged['diff'] > 0]) # Dev 0 is higher (closer to 0)
    dev1_wins = len(merged[merged['diff'] < 0]) # Dev 1 is higher
    draws = len(merged[merged['diff'] == 0])
    
    print(f"📍 Shared Data Points: {total_spots}")
    print(f"\n🏆 PERFORMANCE RESULTS:")
    print(f"  📱 {labels[0]} Better:   {dev0_wins} spots ({dev0_wins/total_spots*100:.1f}%)")
    print(f"  📱 {labels[1]} Better:   {dev1_wins} spots ({dev1_wins/total_spots*100:.1f}%)")
    print(f"  🤝 Exact Ties:         {draws} spots")
    
    avg0 = merged['rsrp_0'].mean()
    avg1 = merged['rsrp_1'].mean()
    
    print(f"\n📡 AVERAGE SIGNAL (RSRP):")
    print(f"  {labels[0]}: {avg0:.2f} dBm")
    print(f"  {labels[1]}: {avg1:.2f} dBm")
    
    diff = avg0 - avg1
    if diff > 0:
        print(f"  ✅ {labels[0]} is stronger by {abs(diff):.2f} dB on average.")
    else:
        print(f"  ✅ {labels[1]} is stronger by {abs(diff):.2f} dB on average.")

def plot_chart(merged, labels):
    plt.figure(figsize=(12, 6))
    plt.plot(merged['rsrp_0'], label=labels[0], color='blue', alpha=0.7, linewidth=1)
    plt.plot(merged['rsrp_1'], label=labels[1], color='orange', alpha=0.7, linewidth=1)
    plt.title(f"Antenna Sensitivity: {labels[0]} vs {labels[1]}")
    plt.ylabel("RSRP (dBm) - Higher is Better")
    plt.xlabel("Measurement Points (Shared Route)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    out_img = "comparison_chart.png"
    plt.savefig(out_img)
    print(f"\n📊 Chart saved to '{out_img}'")

def main():
    print("="*60)
    print("📱 HARDWARE SIGNAL COMPARISON TOOL")
    print("="*60)

    try:
        count = int(input("How many files/devices to compare? (Best results with 2): "))
    except ValueError:
        return
        
    target_op = input("Filter by Operator (e.g., 'A1', 'Yettel') [Press Enter for ALL]: ").strip()
    if target_op == "": target_op = None

    dataframes = []
    labels = []

    for i in range(count):
        print(f"\n--- Device {i+1} ---")
        # Added cleaning for Windows file paths with quotes
        path = input(f"Enter CSV filename for Device {i+1}: ").strip().replace('"', '')
        label = input(f"Enter Label (e.g., 'S25 Ultra'): ").strip()
        
        df = clean_and_load(path, label, target_op)
        if not df.empty:
            dataframes.append(df)
            labels.append(label)

    if len(dataframes) < 2:
        print("❌ Need at least 2 valid files.")
        return

    merged = match_locations(dataframes)
    
    if merged.empty:
        print("⚠️ No matching GPS locations found.")
        return

    if len(labels) == 2:
        generate_battle_report(merged, labels)
    
    plot_chart(merged, labels)
    
    merged.to_csv("comparison_data.csv", index=False)
    print("💾 Data saved to 'comparison_data.csv'")

if __name__ == "__main__":
    main()
