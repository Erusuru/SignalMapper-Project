import pandas as pd
import numpy as np
import glob
import warnings
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
RSRP_EXCELLENT = -80
RSRP_GOOD = -100
RSRP_POOR = -115 
GEO_PRECISION = 4  # ~11 meters
SESSION_TIMEOUT_SECONDS = 300 

# 🏃‍♂️ STATIONARY FILTER
STATIONARY_SPEED_THRESHOLD = -1 
MOBILITY_THRESHOLD = 2.5 

EXPORT_DIR = "exported_results"

# 🚫 BLOCK LIST (Junk Data)
INVALID_LABELS = [
    'NO SERVICE', 'EMERGENCY ONLY', 'EMERGENCY CALLS ONLY', 
    'UNKNOWN', 'SEARCHING', 'NO CONNECTION', 'NOT LOGGED', 'NAN'
]

warnings.filterwarnings("ignore")

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def haversine_vectorized(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    km = R * c
    return km

def sanitize_metrics(df):
    # Sanitize SNR
    if 'snr' in df.columns:
        df['snr'] = pd.to_numeric(df['snr'], errors='coerce')
        # Typical SNR range -20 to +30. 
        # If it's exactly 0.0 often, it might be invalid, but we keep it mathematically.
        df.loc[df['snr'] > 50, 'snr'] = np.nan
        df.loc[df['snr'] < -50, 'snr'] = np.nan
        
    # Sanitize RSRQ (New)
    # Typical LTE RSRQ range is -3 (Excellent) to -19.5 (Edge/Loaded). 
    # Some devices report positive, some report very low negatives.
    if 'rsrq' in df.columns:
        df['rsrq'] = pd.to_numeric(df['rsrq'], errors='coerce')
        # Filter out obvious junk data for RSRQ
        df.loc[df['rsrq'] > 0, 'rsrq'] = np.nan # RSRQ is usually negative in dB
        df.loc[df['rsrq'] < -30, 'rsrq'] = np.nan
        
    return df

def smart_merge_names(op_raw):
    """ Intelligent Name Merger """
    if pd.isna(op_raw): return "UNKNOWN"
    op = str(op_raw).upper().strip()
    
    # 1. Known Aliases
    if "YETTEL" in op: return "YETTEL"
    if "A1" in op: return "A1"
    if "VIVA" in op: return "VIVACOM"
    if "TURK" in op: return "TURK TELEKOM"
    if "VODA" in op: return "VODAFONE"
    if "AVEA" in op: return "TURK TELEKOM" # Legacy Name
    
    # 2. Clean suffix
    if "|" in op:
        op = op.split('|')[0].strip()
    return op

# ==========================================
# 3. DATA LOADING
# ==========================================
def load_new_format(filepath):
    try:
        df = pd.read_csv(filepath)
        df['Operator'] = df['Operator'].apply(smart_merge_names)
        df = df[~df['Operator'].isin(INVALID_LABELS)]
        
        try:
            df['datetime'] = pd.to_datetime(df['Timestamp'], format='mixed', errors='coerce')
        except:
            df['datetime'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        
        df = df.dropna(subset=['datetime', 'Operator'])
        if 'Speed' not in df.columns: df['Speed'] = 0
        df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce')

        # ---------------------------------------------------------
        # UPDATED: Added RSRQ to rename and selection
        # ---------------------------------------------------------
        df = df.rename(columns={
            'Latitude': 'lat', 
            'Longitude': 'lon', 
            'RSRP': 'rsrp', 
            'SNR': 'snr', 
            'RSRQ': 'rsrq',   # <--- Added Map
            'Operator': 'operator', 
            'PCI': 'pci', 
            'Speed': 'speed'
        })
        
        # Ensure columns exist if missing in CSV
        if 'rsrq' not in df.columns: df['rsrq'] = np.nan
        if 'snr' not in df.columns: df['snr'] = np.nan

        df['source'] = 'new_auto'
        return df[['datetime', 'lat', 'lon', 'rsrp', 'snr', 'rsrq', 'speed', 'operator', 'source', 'pci']]
    except Exception as e: 
        print(f"Error reading {filepath}: {e}")
        return pd.DataFrame()

def load_all_csvs():
    all_files = glob.glob("*.csv")
    df_list = []
    print(f"📂 Found {len(all_files)} CSV files.")
    for f in all_files:
        if "signal_map" in f or "mock" in f: continue
        try:
            preview = pd.read_csv(f, nrows=1)
            # Basic check to see if it's the right format
            if 'NetworkType' in preview.columns: 
                df_list.append(load_new_format(f))
        except: pass
        
    if not df_list: return pd.DataFrame()
    df_final = pd.concat(df_list, ignore_index=True)
    return sanitize_metrics(df_final)

# ==========================================
# 4. FILTERING & ANALYSIS LOGIC
# ==========================================
def remove_stationary_data(df):
    """ 
    Keeps data if:
    1. Location changes OR
    2. Signal (RSRP) changes (even if standing still)
    """
    if df.empty: return df
    
    df = df.sort_values('datetime')
    df['lat_r'] = df['lat'].round(5) 
    df['lon_r'] = df['lon'].round(5)
    
    # Keep if Lat changed OR Lon changed OR Signal changed
    mask = (df['lat_r'] != df['lat_r'].shift(1)) | \
           (df['lon_r'] != df['lon_r'].shift(1)) | \
           (df['rsrp'] != df['rsrp'].shift(1)) 
           
    mask.iloc[0] = True 
    
    return df[mask].drop(columns=['lat_r', 'lon_r'])

def calculate_true_duration(df_op):
    df_op = df_op.sort_values('datetime')
    df_op['diff'] = df_op['datetime'].diff().dt.total_seconds()
    valid_duration = df_op[df_op['diff'] < SESSION_TIMEOUT_SECONDS]['diff'].sum()
    return valid_duration / 60.0 

def analyze_data(df):
    if df.empty: return 0, 0
    
    report_buffer = []

    def log(text=""):
        print(text)
        report_buffer.append(str(text))
        
    def log_df(dataframe):
        s = dataframe.to_string()
        print(s)
        report_buffer.append(s)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.options.display.float_format = '{:.1f}'.format

    df_new = df.copy()

    log("\n" + "="*50)
    log("📊 ULTIMATE NETWORK COMPARISON REPORT")
    log(f"Operators Included: {df['operator'].unique()}")
    log("="*50)
    
    # [1] SIGNAL STRENGTH
    log("\n[1] SIGNAL STRENGTH DISTRIBUTION (RSRP)")
    def classify(r):
        if r >= RSRP_EXCELLENT: return '1. Excellent'
        if r >= RSRP_GOOD: return '2. Good'
        if r >= RSRP_POOR: return '3. Fair'
        return '4. Dead Zone'
    
    df_new['qual'] = df_new['rsrp'].apply(classify)
    stats = df_new.groupby(['operator', 'qual']).size().unstack(fill_value=0)
    stats_percent = (stats.div(stats.sum(axis=1), axis=0) * 100)
    log_df(stats_percent)

    # [2] POLLUTION & INTERFERENCE
    log("\n[2] QUALITY ISSUES (Good Signal, Bad Quality)")
    log("    (Criteria: RSRP > Good AND [SNR < 5dB OR RSRQ < -15dB])")
    
    for op in df_new['operator'].unique():
        op_df = df_new[df_new['operator'] == op]
        good_count = len(op_df[op_df['rsrp'] > RSRP_GOOD])
        
        if good_count > 0:
            # Check for bad SNR (traditional pollution)
            bad_snr = len(op_df[(op_df['rsrp'] > RSRP_GOOD) & (op_df['snr'] < 5)])
            
            # Check for bad RSRQ (Interference/Load) - helpful if SNR is 0.0
            bad_rsrq = len(op_df[(op_df['rsrp'] > RSRP_GOOD) & (op_df['rsrq'] < -15)])
            
            # Combined bad quality index (Unique points)
            bad_combined = len(op_df[(op_df['rsrp'] > RSRP_GOOD) & ((op_df['snr'] < 5) | (op_df['rsrq'] < -15))])

            log(f"  - {op}:")
            log(f"      Combined 'Polluted' Samples: {(bad_combined/good_count)*100:.1f}%")
            log(f"      (Breakdown: Low SNR: {(bad_snr/good_count)*100:.1f}% | Poor RSRQ: {(bad_rsrq/good_count)*100:.1f}%)")
        else:
            log(f"  - {op}: No 'Good' coverage samples to analyze for pollution.")

    # [3] HANDOVER STABILITY
    log("\n[3] HANDOVER STABILITY (Ping-Pong Effect)")
    df_sorted = df_new.sort_values(['operator', 'datetime'])
    for op in df_new['operator'].unique():
        op_df = df_sorted[df_sorted['operator'] == op].copy()
        true_duration_min = calculate_true_duration(op_df)
        
        op_df['pci_shift'] = op_df['pci'].shift(1)
        switches = len(op_df[op_df['pci'] != op_df['pci_shift']]) - 1
        if switches < 0: switches = 0

        if true_duration_min > 1:
            rate = switches / true_duration_min
            log(f"  - {op}: {rate:.2f} switches/min ({switches} in {true_duration_min:.1f} mins)")
    
    # [4] CONSISTENCY
    log("\n[4] QUALITY & CONSISTENCY SCORES")
    stats_df = df_new.groupby('operator').agg({
        'rsrp': ['mean', 'std'], 
        'snr': 'mean',
        'rsrq': 'mean' # Added RSRQ here
    })
    stats_df.columns = ['Avg RSRP', 'Stability (StdDev)', 'Avg SNR', 'Avg RSRQ']
    log_df(stats_df)

    # [5] THE STREET FIGHT
    log("\n[5] THE STREET FIGHT (Head-to-Head - RSRP)")
    df_new['grid_id'] = list(zip(df_new['lat'].round(GEO_PRECISION), df_new['lon'].round(GEO_PRECISION)))
    pivot = df_new.pivot_table(index='grid_id', columns='operator', values='rsrp', aggfunc='mean')
    
    cols = pivot.columns.tolist()
    if len(cols) >= 2:
        import itertools
        for op1, op2 in itertools.combinations(cols, 2):
            comp = pivot[[op1, op2]].dropna()
            if not comp.empty:
                op1_w = (comp[op1] > comp[op2]).sum()
                op2_w = (comp[op2] > comp[op1]).sum()
                log(f"  ⚔️  {op1} vs {op2} (Based on {len(comp)} shared locations):")
                log(f"     🏆 {op1}: Wins {op1_w} spots ({(op1_w/len(comp))*100:.1f}%)")
                log(f"     🏆 {op2}: Wins {op2_w} spots ({(op2_w/len(comp))*100:.1f}%)")

    # [6] MOBILITY
    log("\n[6] MOBILITY PROFILE")
    for op in df_new['operator'].unique():
        op_df = df_new[df_new['operator'] == op]
        total_pts = len(op_df)
        if total_pts == 0: continue
        walking_count = len(op_df[op_df['speed'] < MOBILITY_THRESHOLD])
        vehicle_count = len(op_df[op_df['speed'] >= MOBILITY_THRESHOLD])
        log(f"  - {op}: Walking { (walking_count/total_pts)*100:.0f}% | Vehicle { (vehicle_count/total_pts)*100:.0f}%")

    # [7] INFRASTRUCTURE
    log("\n[7] UNIQUE TOWER INFRASTRUCTURE")
    for op in df_new['operator'].unique():
        op_df = df_new[df_new['operator'] == op]
        unique_pcis = op_df['pci'].dropna().unique()
        log(f"  - {op}: {len(unique_pcis)} Unique Towers/Sectors")

    # [8] DISTANCE
    log("\n[8] DISTANCE & COVERAGE ANALYSIS")
    dist_df = df_new.sort_values(['operator', 'datetime']).copy()
    dist_df['prev_lat'] = dist_df.groupby('operator')['lat'].shift(1)
    dist_df['prev_lon'] = dist_df.groupby('operator')['lon'].shift(1)
    dist_df['dist_km'] = haversine_vectorized(dist_df['lat'], dist_df['lon'], dist_df['prev_lat'], dist_df['prev_lon'])
    dist_df = dist_df[dist_df['dist_km'] < 1.0] 

    total_dist_stats = dist_df.groupby('operator')['dist_km'].sum()
    unique_counts = df_new.groupby('operator')['grid_id'].nunique()
    
    for op in df_new['operator'].unique():
        t_dist = total_dist_stats.get(op, 0)
        u_dist = unique_counts.get(op, 0) * 0.011 
        
        log(f"  - {op}:")
        log(f"    📏 Total Travelled:   {t_dist:.2f} km")
        log(f"    🗺️  Unique Coverage:   ~{u_dist:.2f} km")

    log("\n" + "="*50)
    report_path = os.path.join(EXPORT_DIR, 'network_comparison_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_buffer))
    print(f"\n📄 Report saved to: {report_path}")
    
    return total_dist_stats.sum(), unique_counts.sum() * 0.011

def spatial_averaging(df):
    if df.empty: return df
    df['grid_lat'] = df['lat'].round(GEO_PRECISION)
    df['grid_lon'] = df['lon'].round(GEO_PRECISION)
    
    # ---------------------------------------------------------
    # UPDATED: Added rsrq to aggregation
    # ---------------------------------------------------------
    df_agg = df.groupby(['grid_lat', 'grid_lon', 'operator']).agg({
        'rsrp': 'mean', 
        'snr': 'mean', 
        'rsrq': 'mean',  # <--- Now averaging RSRQ
        'lat': 'mean', 
        'lon': 'mean',
        'pci': lambda x: x.mode()[0] if not x.mode().empty else np.nan
    }).reset_index()
    
    return df_agg

# ==========================================
# 5. EXECUTION
# ==========================================
if __name__ == "__main__":
    df_combined = load_all_csvs()
    
    if not df_combined.empty:
        os.makedirs(EXPORT_DIR, exist_ok=True)
        
        # 1. Filter
        df_clean = remove_stationary_data(df_combined)
        
        if df_clean.empty:
            print("❌ All data was stationary!")
            exit()
            
        # 2. Analyze
        total_km_travelled, total_unique_km = analyze_data(df_clean)
        
        # 3. Export Maps
        df_map = spatial_averaging(df_clean)
        print(f"💾 EXPORTING CSV MAPS TO '{EXPORT_DIR}/' ...")
        
        for op in df_map['operator'].unique():
            safe_name = "".join(x for x in op if x.isalnum() or x in " _-").strip()
            df_op = df_map[df_map['operator'] == op]
            path = os.path.join(EXPORT_DIR, f'signal_map_{safe_name}.csv')
            
            # Export includes RSRQ now
            df_op.to_csv(path, index=False)
            print(f"  ✅ Saved {op} map (with RSRQ)")
        
        # 4. Summary
        print("\n" + "="*50)
        print("📉 DATA VOLUME & DISTANCE SUMMARY")
        print("="*50)
        
        count_clean = len(df_clean)
        count_exported = len(df_map)
        
        print(f"1. Samples After Cleaning:      {count_clean:,}")
        print(f"2. Exported Map Points:         {count_exported:,}")
        print(f"3. Total Distance Travelled:    {total_km_travelled:.2f} km")
        print(f"4. Total Unique Coverage Est:   ~{total_unique_km:.2f} km")
        print("="*50 + "\n")

    else:
        print("❌ No CSV files found.")
