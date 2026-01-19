import pandas as pd
import numpy as np
import glob
import warnings
import os
import matplotlib.pyplot as plt

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

# 🧹 CLEANING THRESHOLDS
MIN_SAMPLES_FOR_REPORT = 50 
DEAD_ZONE_THRESHOLD = -130 

EXPORT_DIR = "exported_results"
CHARTS_DIR = os.path.join(EXPORT_DIR, "charts")

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
    if 'snr' in df.columns:
        df['snr'] = pd.to_numeric(df['snr'], errors='coerce')
        df.loc[df['snr'] > 50, 'snr'] = np.nan 
        df.loc[df['snr'] < -50, 'snr'] = np.nan
        
    if 'rsrq' in df.columns:
        df['rsrq'] = pd.to_numeric(df['rsrq'], errors='coerce')
        df.loc[df['rsrq'] > 0, 'rsrq'] = np.nan 
        df.loc[df['rsrq'] < -30, 'rsrq'] = np.nan
        
    return df

def smart_merge_names(op_raw):
    if pd.isna(op_raw): return "UNKNOWN"
    op = str(op_raw).upper().strip()
    
    if "YETTEL" in op: return "YETTEL"
    if "A1" in op: return "A1"
    if "VIVA" in op: return "VIVACOM"
    if "TURK" in op: return "TURK TELEKOM"
    if "VODA" in op: return "VODAFONE"
    if "AVEA" in op: return "TURK TELEKOM"
    
    if "|" in op:
        op = op.split('|')[0].strip()
    return op

def standardize_tech(raw_tech):
    if pd.isna(raw_tech): return "UNKNOWN"
    t = str(raw_tech).upper()
    
    if "NR" in t: return "5G"
    if "LTE" in t: return "4G"
    if "WCDMA" in t or "HSPA" in t or "UMTS" in t or "3G" in t: return "3G"
    if "GSM" in t or "EDGE" in t or "GPRS" in t or "2G" in t: return "2G"
    
    return "Other"

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

        df = df.rename(columns={
            'Latitude': 'lat', 
            'Longitude': 'lon', 
            'RSRP': 'rsrp', 
            'SNR': 'snr', 
            'RSRQ': 'rsrq',
            'Operator': 'operator', 
            'PCI': 'pci', 
            'Speed': 'speed',
            'NetworkType': 'tech_raw'
        })
        
        if 'tech_raw' in df.columns:
            df['tech'] = df['tech_raw'].apply(standardize_tech)
        else:
            df['tech'] = "Unknown"

        if 'rsrq' not in df.columns: df['rsrq'] = np.nan
        if 'snr' not in df.columns: df['snr'] = np.nan

        df['source'] = 'new_auto'
        return df[['datetime', 'lat', 'lon', 'rsrp', 'snr', 'rsrq', 'speed', 'operator', 'tech', 'source', 'pci']]
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
    if df.empty: return df
    
    df = df.sort_values('datetime')
    df['lat_r'] = df['lat'].round(5) 
    df['lon_r'] = df['lon'].round(5)
    
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

# ==========================================
# 5. CHARTING ENGINE (INTEGRATED)
# ==========================================
def generate_internal_charts(df_clean):
    """ Generates PNG charts from the dataframe currently in memory """
    if df_clean.empty: return

    print("📊 Generating Visual Charts...")
    os.makedirs(CHARTS_DIR, exist_ok=True)
    
    # Create Label (e.g. A1 (4G))
    df_chart = df_clean.copy()
    df_chart['label'] = df_chart['operator'] + " (" + df_chart['tech'] + ")"
    
    # Use Agg backend to work on servers without display
    plt.switch_backend('Agg')
    plt.style.use('ggplot')

    # --- CHART 1: Average Signal Strength (Bar) ---
    plt.figure(figsize=(12, 7))
    avg_rsrp = df_chart.groupby('label')['rsrp'].mean().sort_values(ascending=False)
    
    colors = []
    for x in avg_rsrp.values:
        if x > -90: colors.append('#2ecc71') # Green
        elif x > -100: colors.append('#f1c40f') # Yellow
        elif x > -110: colors.append('#e67e22') # Orange
        else: colors.append('#e74c3c') # Red

    ax = avg_rsrp.plot(kind='bar', color=colors, width=0.7)
    plt.title('Average Signal Strength (RSRP)', fontsize=16)
    plt.ylabel('RSRP (dBm)', fontsize=12)
    plt.xlabel('Operator (Tech)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add labels
    for i, v in enumerate(avg_rsrp):
        ax.text(i, v + 1, f"{v:.1f}", ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "benchmark_signal_strength.png"), dpi=300)
    print("  ✅ Saved: charts/benchmark_signal_strength.png")
    plt.close()

    # --- CHART 2: Quality Distribution (Stacked) ---
    def classify(r):
        if r >= -85: return 'Excellent'
        if r >= -100: return 'Good'
        if r >= -115: return 'Fair'
        return 'Poor'

    df_chart['category'] = df_chart['rsrp'].apply(classify)
    dist = df_chart.groupby(['label', 'category']).size().unstack(fill_value=0)
    dist_pct = dist.div(dist.sum(axis=1), axis=0) * 100
    
    col_order = ['Excellent', 'Good', 'Fair', 'Poor']
    existing_cols = [c for c in col_order if c in dist_pct.columns]
    dist_pct = dist_pct[existing_cols]
    
    color_map = {'Excellent': '#27ae60', 'Good': '#2ecc71', 'Fair': '#f1c40f', 'Poor': '#c0392b'}
    stack_colors = [color_map[c] for c in existing_cols]

    ax2 = dist_pct.plot(kind='bar', stacked=True, figsize=(12, 7), color=stack_colors)
    plt.title('Signal Quality Distribution (%)', fontsize=16)
    plt.ylabel('Percentage', fontsize=12)
    plt.xlabel('Operator', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.legend(bbox_to_anchor=(1.0, 1.05))
    
    for c in ax2.containers:
        ax2.bar_label(c, fmt='%.0f%%', label_type='center', color='white', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "benchmark_quality_dist.png"), dpi=300)
    print("  ✅ Saved: charts/benchmark_quality_dist.png")
    plt.close()

# ==========================================
# 6. MAIN ANALYSIS
# ==========================================
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

    # --- 1. CALCULATE GRID FIRST ---
    df_new['grid_id'] = list(zip(df_new['lat'].round(GEO_PRECISION), df_new['lon'].round(GEO_PRECISION)))

    # --- 2. FILTER OUT "GHOST" / DEAD TECHNOLOGIES ---
    counts = df_new.groupby(['operator', 'tech']).size()
    valid_counts = counts[counts > MIN_SAMPLES_FOR_REPORT].index
    means = df_new.groupby(['operator', 'tech'])['rsrp'].mean()
    valid_means = means[means > DEAD_ZONE_THRESHOLD].index 
    valid_groups = valid_counts.intersection(valid_means)
    
    # Filter the DataFrame used for Report AND Charts
    df_clean_report = df_new.set_index(['operator', 'tech']).loc[valid_groups].reset_index()

    # --- GENERATE CHARTS NOW (Using the filtered data) ---
    generate_internal_charts(df_clean_report)

    log("\n" + "="*50)
    log("📊 ULTIMATE NETWORK COMPARISON REPORT")
    log(f"Operators Included: {df_clean_report['operator'].unique()}")
    log("="*50)
    
    # [1] SIGNAL STRENGTH
    log("\n[1] SIGNAL STRENGTH DISTRIBUTION (RSRP)")
    def classify(r):
        if r >= RSRP_EXCELLENT: return '1. Excellent'
        if r >= RSRP_GOOD: return '2. Good'
        if r >= RSRP_POOR: return '3. Fair'
        return '4. Dead Zone'
    
    df_clean_report['qual'] = df_clean_report['rsrp'].apply(classify)
    stats = df_clean_report.groupby(['operator', 'tech', 'qual']).size().unstack(fill_value=0)
    stats_percent = (stats.div(stats.sum(axis=1), axis=0) * 100)
    log_df(stats_percent)

    # [2] POLLUTION
    log("\n[2] QUALITY ISSUES (RSRP > Good but Low Quality)")
    for op in df_clean_report['operator'].unique():
        op_df = df_clean_report[df_clean_report['operator'] == op]
        good_count = len(op_df[op_df['rsrp'] > RSRP_GOOD])
        
        if good_count > 0:
            missing_snr = op_df['snr'].isna().sum()
            missing_ratio = missing_snr / len(op_df)
            zero_count = (op_df['snr'] == 0.0).sum()
            zero_ratio = zero_count / len(op_df)
            
            if missing_ratio > 0.5 or zero_ratio > 0.5:
                log(f"  - {op}: ⚠️ SNR Unsupported (Sensor Missing/Incompatible)")
            else:
                bad_combined = len(op_df[(op_df['rsrp'] > RSRP_GOOD) & ((op_df['snr'] < 5) | (op_df['rsrq'] < -15))])
                log(f"  - {op}: {(bad_combined/good_count)*100:.1f}% Polluted")
        else:
            log(f"  - {op}: Insufficient 'Good' signal samples.")

    # [3] HANDOVER STABILITY
    log("\n[3] HANDOVER STABILITY")
    df_sorted = df_clean_report.sort_values(['operator', 'datetime'])
    for op in df_clean_report['operator'].unique():
        op_df = df_sorted[df_sorted['operator'] == op].copy()
        true_duration_min = calculate_true_duration(op_df)
        
        op_df['pci_shift'] = op_df['pci'].shift(1)
        switches = len(op_df[op_df['pci'] != op_df['pci_shift']]) - 1
        if switches < 0: switches = 0

        if true_duration_min > 1:
            rate = switches / true_duration_min
            log(f"  - {op}: {rate:.2f} switches/min")
    
    # [4] CONSISTENCY
    log("\n[4] QUALITY SCORES (By Tech)")
    stats_df = df_clean_report.groupby(['operator', 'tech']).agg({
        'rsrp': ['mean', 'std'], 
        'snr': 'mean',
        'rsrq': 'mean'
    })
    stats_df.columns = ['Avg RSRP', 'Stability', 'Avg SNR', 'Avg RSRQ']
    log_df(stats_df)

    # [5] MOBILITY
    log("\n[5] MOBILITY PROFILE")
    for op in df_clean_report['operator'].unique():
        op_df = df_clean_report[df_clean_report['operator'] == op]
        total_pts = len(op_df)
        if total_pts == 0: continue
        
        vehicle_count = len(op_df[op_df['speed'] >= MOBILITY_THRESHOLD])
        vehicle_pct = (vehicle_count / total_pts) * 100
        walking_pct = 100 - vehicle_pct
        log(f"  - {op}: {vehicle_pct:.0f}% Vehicle | {walking_pct:.0f}% Walking")

    # [6] DISTANCE
    log("\n[6] DISTANCE & COVERAGE")
    dist_df = df_clean_report.sort_values(['operator', 'datetime']).copy()
    dist_df['prev_lat'] = dist_df.groupby('operator')['lat'].shift(1)
    dist_df['prev_lon'] = dist_df.groupby('operator')['lon'].shift(1)
    dist_df['dist_km'] = haversine_vectorized(dist_df['lat'], dist_df['lon'], dist_df['prev_lat'], dist_df['prev_lon'])
    dist_df = dist_df[dist_df['dist_km'] < 1.0] 

    total_dist_stats = dist_df.groupby('operator')['dist_km'].sum()
    unique_counts = df_clean_report.groupby('operator')['grid_id'].nunique() 

    for op in df_clean_report['operator'].unique():
        t_dist = total_dist_stats.get(op, 0)
        u_dist = unique_counts.get(op, 0) * 0.011 
        log(f"  - {op}: {t_dist:.2f} km Driven | ~{u_dist:.2f} km Unique Coverage")

    log("\n" + "="*50)
    report_path = os.path.join(EXPORT_DIR, 'network_comparison_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_buffer))
    print(f"📄 Report saved to: {report_path}")
    
    return total_dist_stats.sum(), unique_counts.sum() * 0.011

def spatial_averaging(df):
    if df.empty: return df
    df['grid_lat'] = df['lat'].round(GEO_PRECISION)
    df['grid_lon'] = df['lon'].round(GEO_PRECISION)
    
    df_agg = df.groupby(['grid_lat', 'grid_lon', 'operator', 'tech']).agg({
        'rsrp': 'mean', 
        'snr': 'mean', 
        'rsrq': 'mean',
        'lat': 'mean', 
        'lon': 'mean',
        'pci': lambda x: x.mode()[0] if not x.mode().empty else np.nan
    }).reset_index()
    
    return df_agg

# ==========================================
# 7. EXECUTION
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
            
        # 2. Analyze (Now includes Chart Generation!)
        try:
            total_km_travelled, total_unique_km = analyze_data(df_clean)
        except Exception as e:
            print(f"❌ Analysis Failed: {e}")
            import traceback
            traceback.print_exc()
            total_km_travelled = 0
            total_unique_km = 0
        
        # 3. Export Maps (SPLIT BY TECH)
        df_map = spatial_averaging(df_clean)
        print(f"\n💾 EXPORTING CSV MAPS TO '{EXPORT_DIR}/' ...")
        
        unique_combinations = df_map[['operator', 'tech']].drop_duplicates()
        
        for index, row in unique_combinations.iterrows():
            op_name = row['operator']
            tech_name = row['tech']
            
            df_op_tech = df_map[(df_map['operator'] == op_name) & (df_map['tech'] == tech_name)]
            avg_signal = df_op_tech['rsrp'].mean()
            
            if len(df_op_tech) > MIN_SAMPLES_FOR_REPORT and avg_signal > DEAD_ZONE_THRESHOLD:
                safe_op = "".join(x for x in op_name if x.isalnum() or x in " _-").strip().replace(" ", "_")
                safe_tech = tech_name.replace(" ", "_")
                filename = f"signal_map_{safe_op}_{safe_tech}.csv"
                path = os.path.join(EXPORT_DIR, filename)
                df_op_tech.to_csv(path, index=False)
                print(f"  ✅ Saved: {filename} ({len(df_op_tech)} pts)")
            else:
                print(f"  ⚠️ Skipped: {op_name} {tech_name} (Ghost Data/Dead Zone)")
        
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
