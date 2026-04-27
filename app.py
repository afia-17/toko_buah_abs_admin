import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import io

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Admin – Toko Buah ABS",
    page_icon="📊",
    layout="wide",
)

# ─── AUTH (password sederhana) ────────────────────────────────────────────────
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "abs2024")

def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Login Admin – Toko Buah ABS")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if pw == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah.")
        st.stop()

check_auth()

# ─── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
SHEET_ID = st.secrets.get("SHEET_ID", "")

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_data(ttl=60)
def load_orders():
    client = get_client()
    if not client or not SHEET_ID:
        # Demo data jika belum ada koneksi
        demo = {
            "Tanggal": pd.date_range("2024-01-01", periods=30, freq="D").strftime("%Y-%m-%d").tolist(),
            "Waktu":   ["10:00"]*30,
            "Nama":    [f"Pelanggan {i}" for i in range(1,31)],
            "WhatsApp":[f"08123456{i:04d}" for i in range(1,31)],
            "Alamat":  ["Bogor"]*30,
            "Item":    ["Mangga x2; Jeruk x3"]*30,
            "Total (Rp)": [i*15000 for i in range(1,31)],
            "Status":  ["Selesai"]*25 + ["Baru"]*5,
        }
        return pd.DataFrame(demo)
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("orders")
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_saran():
    client = get_client()
    if not client or not SHEET_ID:
        return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("saran")
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }

.kpi-card {
    background: linear-gradient(135deg, #1a6b1f, #2e9e36);
    color: white;
    padding: 1.5rem;
    border-radius: 16px;
    text-align: center;
    box-shadow: 0 4px 18px rgba(30,120,40,0.25);
}
.kpi-val { font-size: 2rem; font-weight: 700; }
.kpi-lbl { font-size: 0.85rem; opacity: 0.88; }

.kpi-card.yellow {
    background: linear-gradient(135deg, #e6a800, #f7c948);
    color: #333;
}
.kpi-card.blue {
    background: linear-gradient(135deg, #1565c0, #1e88e5);
    color: white;
}
.kpi-card.red {
    background: linear-gradient(135deg, #b71c1c, #e53935);
    color: white;
}

.section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #1a6b1f;
    border-bottom: 3px solid #f7c948;
    padding-bottom: 0.3rem;
    margin: 1.5rem 0 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("# 📊 Dashboard Admin – Toko Buah ABS")
st.caption(f"Data diperbarui otomatis · Terakhir diakses: {datetime.datetime.now().strftime('%d %b %Y, %H:%M')}")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
df = load_orders()
df_saran = load_saran()

if df.empty:
    st.warning("Belum ada data pesanan.")
    st.stop()

# Konversi tipe
df["Total (Rp)"] = pd.to_numeric(df["Total (Rp)"], errors="coerce").fillna(0)
df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")

# ─── FILTER ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🔎 Filter Periode</div>', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns(3)
with fc1:
    filter_mode = st.selectbox("Tampilkan", ["Semua", "Harian", "Bulanan", "Tahunan"])
with fc2:
    if filter_mode == "Harian":
        sel_date = st.date_input("Pilih Tanggal", datetime.date.today())
        mask = df["Tanggal"].dt.date == sel_date
    elif filter_mode == "Bulanan":
        sel_month = st.selectbox("Bulan", range(1,13), index=datetime.date.today().month-1,
                                  format_func=lambda m: datetime.date(2000,m,1).strftime("%B"))
        mask = df["Tanggal"].dt.month == sel_month
    elif filter_mode == "Tahunan":
        years = sorted(df["Tanggal"].dt.year.dropna().unique().tolist(), reverse=True)
        sel_year = st.selectbox("Tahun", years if years else [datetime.date.today().year])
        mask = df["Tanggal"].dt.year == sel_year
    else:
        mask = pd.Series([True]*len(df))

df_f = df[mask].copy()

# ─── KPI CARDS ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📈 Ringkasan Statistik</div>', unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
total_pesanan  = len(df_f)
total_pemasukan = df_f["Total (Rp)"].sum()
rata_order     = df_f["Total (Rp)"].mean() if total_pesanan else 0
pesanan_baru   = len(df_f[df_f["Status"] == "Baru"]) if "Status" in df_f.columns else 0

with k1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-val">{total_pesanan}</div><div class="kpi-lbl">Total Pesanan</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card yellow"><div class="kpi-val">Rp {total_pemasukan:,.0f}</div><div class="kpi-lbl">Total Pemasukan</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card blue"><div class="kpi-val">Rp {rata_order:,.0f}</div><div class="kpi-lbl">Rata-rata per Pesanan</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-card red"><div class="kpi-val">{pesanan_baru}</div><div class="kpi-lbl">Pesanan Baru (Belum Diproses)</div></div>', unsafe_allow_html=True)

st.write("")

# ─── CHART: Pemasukan per Hari ────────────────────────────────────────────────
st.markdown('<div class="section-title">📅 Grafik Pemasukan</div>', unsafe_allow_html=True)
if not df_f.empty:
    chart_df = df_f.groupby(df_f["Tanggal"].dt.date)["Total (Rp)"].sum().reset_index()
    chart_df.columns = ["Tanggal", "Pemasukan (Rp)"]
    st.line_chart(chart_df.set_index("Tanggal"))
else:
    st.info("Tidak ada data pada periode ini.")

# ─── TABEL PESANAN ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 Daftar Pesanan</div>', unsafe_allow_html=True)

if "Status" in df_f.columns:
    status_filter = st.multiselect("Filter Status", df_f["Status"].unique().tolist(),
                                    default=df_f["Status"].unique().tolist())
    df_show = df_f[df_f["Status"].isin(status_filter)]
else:
    df_show = df_f

st.dataframe(df_show.sort_values("Tanggal", ascending=False), use_container_width=True)

# Update status pesanan
if "Status" in df_f.columns and not df_show.empty:
    st.markdown("**Update Status Pesanan:**")
    us1, us2, us3 = st.columns(3)
    with us1:
        idx_upd = st.number_input("Nomor baris (0=pertama)", min_value=0,
                                   max_value=max(0, len(df_show)-1), value=0)
    with us2:
        new_status = st.selectbox("Status Baru", ["Baru","Diproses","Dalam Pengiriman","Selesai","Dibatalkan"])
    with us3:
        st.write("")
        if st.button("Update"):
            client = get_client()
            if client and SHEET_ID:
                try:
                    sh = client.open_by_key(SHEET_ID)
                    ws = sh.worksheet("orders")
                    real_row = df_show.index[idx_upd] + 2  # +2: header + 1-based
                    ws.update_cell(real_row, 8, new_status)
                    st.success(f"Status diperbarui ke: {new_status}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal update: {e}")

# ─── EXPORT EXCEL ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">⬇️ Ekspor Laporan</div>', unsafe_allow_html=True)
ex1, ex2 = st.columns(2)

def to_excel(dataframe):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Pesanan")
    return buf.getvalue()

with ex1:
    st.download_button(
        "⬇️ Download Laporan (Periode Dipilih)",
        data=to_excel(df_f),
        file_name=f"laporan_abs_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with ex2:
    st.download_button(
        "⬇️ Download Semua Data",
        data=to_excel(df),
        file_name=f"semua_data_abs_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ─── KRITIK & SARAN ──────────────────────────────────────────────────────────
if not df_saran.empty:
    st.markdown('<div class="section-title">💬 Kritik & Saran Pelanggan</div>', unsafe_allow_html=True)
    if "Rating" in df_saran.columns:
        avg_rating = pd.to_numeric(df_saran["Rating"], errors="coerce").mean()
        st.metric("⭐ Rata-rata Rating", f"{avg_rating:.1f} / 5.0")
    st.dataframe(df_saran, use_container_width=True)

# ─── LOGOUT ──────────────────────────────────────────────────────────────────
st.divider()
if st.button("🔓 Logout"):
    st.session_state.authenticated = False
    st.rerun()
