import hashlib
import sqlite3
import streamlit as st

# --- KONFIGURASI DATABASE & KEAMANAN ---
DB_NAME = "portfolio_siswa.db"


def hash_password(password):
  return hashlib.sha256(password.encode()).hexdigest()


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  # 1. Tabel Pengguna (Menyimpan akun Admin dan Siswa beserta role-nya)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nama_lengkap TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

  # 2. Tabel Portofolio (Terhubung dengan username pembuatnya)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username_pembuat TEXT NOT NULL,
            nama_siswa TEXT NOT NULL,
            judul_karya TEXT NOT NULL,
            kategori TEXT NOT NULL,
            deskripsi TEXT NOT NULL,
            link_repo TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)
  conn.commit()

  # Membuat Akun Admin Utama secara otomatis jika belum ada
  # Username: admin | Password: password123
  cursor.execute("SELECT * FROM users WHERE username = 'admin'")
  if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO users (username, nama_lengkap, password_hash, role) VALUES"
        " (?, ?, ?, ?)",
        ("admin", "Administrator Sekolah", hash_password("password123"), "admin"),
    )
    conn.commit()

  conn.close()


init_db()


# --- FUNGSI AUTENTIKASI ---
def register_user(username, nama_lengkap, password):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  try:
    cursor.execute(
        "INSERT INTO users (username, nama_lengkap, password_hash, role) VALUES"
        " (?, ?, ?, 'siswa')",
        (username.strip(), nama_lengkap.strip(), hash_password(password)),
    )
    conn.commit()
    return True, "Registrasi berhasil! Silakan login menggunakan akun barumu."
  except sqlite3.IntegrityError:
    return False, "Username sudah digunakan, silakan pilih username lain."
  finally:
    conn.close()


def login_user(username, password):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT username, nama_lengkap, role FROM users WHERE username = ? AND"
      " password_hash = ?",
      (username.strip(), hash_password(password)),
  )
  user = cursor.fetchone()
  conn.close()
  return user  # Mengembalikan tuple (username, nama_lengkap, role) atau None


# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Sistem Portofolio Digital", page_icon="🎓", layout="wide"
)

# Inisialisasi Session State
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.username = ""
  st.session_state.nama_lengkap = ""
  st.session_state.role = ""

# --- SIDEBAR: AKUN & NAVIGASI ---
st.sidebar.title("🎓 Portofolio Digital")

if not st.session_state.logged_in:
  auth_mode = st.sidebar.radio("Akses Akun:", ["Login", "Daftar Akun Siswa"])

  if auth_mode == "Login":
    with st.sidebar.form("form_login"):
      st.subheader("🔐 Masuk ke Sistem")
      in_user = st.text_input("Username")
      in_pass = st.text_input("Password", type="password")
      btn_login = st.form_submit_button("Login")

      if btn_login:
        user_data = login_user(in_user, in_pass)
        if user_data:
          st.session_state.logged_in = True
          st.session_state.username = user_data[0]
          st.session_state.nama_lengkap = user_data[1]
          st.session_state.role = user_data[2]
          st.rerun()
        else:
          st.error("Username atau Password salah!")

  elif auth_mode == "Daftar Akun Siswa":
    with st.sidebar.form("form_register"):
      st.subheader("📝 Buat Akun Siswa")
      reg_nama = st.text_input("Nama Lengkap")
      reg_user = st.text_input("Username Baru")
      reg_pass = st.text_input("Password Baru", type="password")
      btn_reg = st.form_submit_button("Daftar Sekarang")

      if btn_reg:
        if reg_nama and reg_user and reg_pass:
          sukses, pesan = register_user(reg_user, reg_nama, reg_pass)
          if sukses:
            st.success(pesan)
          else:
            st.error(pesan)
        else:
          st.warning("Semua kolom wajib diisi!")

  st.sidebar.markdown("---")
  menu = "Galeri Publik"
  st.sidebar.info(
      "Login sebagai **Siswa** untuk mengirim karya, atau login sebagai"
      " **Admin** untuk memvalidasi request."
  )

else:
  # Tampilan Sidebar jika sudah Login
  role_badge = (
      "🛡️ ADMIN" if st.session_state.role == "admin" else "👨‍🎓 SISWA"
  )
  st.sidebar.success(f"**{st.session_state.nama_lengkap}**\n\nRole: `{role_badge}`")

  if st.session_state.role == "siswa":
    menu = st.sidebar.radio(
        "Menu Navigasi:", ["Galeri Publik", "Portofolio Saya (Submit & Status)"]
    )
  elif st.session_state.role == "admin":
    menu = st.sidebar.radio(
        "Menu Navigasi:",
        ["Galeri Publik", "Validasi Request Siswa (Admin)"],
    )

  st.sidebar.markdown("---")
  if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.nama_lengkap = ""
    st.session_state.role = ""
    st.rerun()


# ==========================================
# HALAMAN 1: GALERI PUBLIK (SEMUA BISA LIHAT)
# ==========================================
if menu == "Galeri Publik":
  st.title("🌟 Galeri Portofolio Digital")
  st.markdown("Kumpulan karya akademik yang telah diverifikasi dan disetujui oleh Admin.")

  col1, col2 = st.columns([2, 1])
  with col1:
    search_query = st.text_input("🔍 Cari Judul Karya atau Nama Pembuat...")
  with col2:
    filter_kat = st.selectbox(
        "Filter Kategori",
        [
            "Semua Kategori",
            "Informatika & Pemrograman",
            "Sains & Riset",
            "Multimedia & Desain",
            "Lainnya",
        ],
    )

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT nama_siswa, judul_karya, kategori, deskripsi, link_repo FROM"
      " portfolios WHERE status = 'Approved' ORDER BY id DESC"
  )
  data_approved = cursor.fetchall()
  conn.close()

  # Terapkan filter pencarian & kategori
  hasil_filter = []
  for item in data_approved:
    nama, judul, kat, desk, link = item
    cocok_teks = (
        search_query.lower() in nama.lower()
        or search_query.lower() in judul.lower()
    )
    cocok_kat = filter_kat == "Semua Kategori" or kat == filter_kat
    if cocok_teks and cocok_kat:
      hasil_filter.append(item)

  if not hasil_filter:
    st.info("Belum ada portofolio yang tampil di galeri publik.")
  else:
    st.markdown("---")
    for nama, judul, kat, desk, link in hasil_filter:
      with st.container():
        st.subheader(f"📌 {judul}")
        st.markdown(f"**Oleh:** {nama} | **Kategori:** `{kat}`")
        st.write(desk)
        st.markdown(f"[🔗 Buka Tautan Karya / Repositori]({link})")
        st.markdown("---")


# ==========================================
# HALAMAN 2: DASHBOARD KHUSUS AKUN SISWA
# ==========================================
elif menu == "Portofolio Saya (Submit & Status)":
  st.title(f"📂 Ruang Portofolio: {st.session_state.nama_lengkap}")

  tab1, tab2 = st.tabs(["➕ Ajukan Portofolio Baru", "📋 Riwayat & Status Request Saya"])

  # TAB 1: Form Pengajuan Karya
  with tab1:
    st.markdown("Kirim karya terbaikmu untuk diperiksa dan disetujui oleh Admin.")
    with st.form("form_karya_siswa", clear_on_submit=True):
      judul = st.text_input("Judul Karya / Proyek")
      kategori = st.selectbox(
          "Kategori",
          [
              "Informatika & Pemrograman",
              "Sains & Riset",
              "Multimedia & Desain",
              "Lainnya",
          ],
      )
      deskripsi = st.text_area("Deskripsi Singkat Karya")
      link = st.text_input("Link Proyek (GitHub / Google Drive / Web Demo)")
      submit_karya = st.form_submit_button("Kirim Request ke Admin")

      if submit_karya:
        if judul and deskripsi and link:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              """
              INSERT INTO portfolios (username_pembuat, nama_siswa, judul_karya, kategori, deskripsi, link_repo, status)
              VALUES (?, ?, ?, ?, ?, ?, 'Pending')
              """,
              (
                  st.session_state.username,
                  st.session_state.nama_lengkap,
                  judul,
                  kategori,
                  deskripsi,
                  link,
              ),
          )
          conn.commit()
          conn.close()
          st.success("Request berhasil dikirim! Status saat ini: Pending.")
          st.rerun()
        else:
          st.warning("Harap isi semua kolom terlebih dahulu.")

  # TAB 2: Daftar Karya Milik Siswa Tersebut
  with tab2:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, judul_karya, kategori, deskripsi, link_repo, status FROM"
        " portfolios WHERE username_pembuat = ? ORDER BY id DESC",
        (st.session_state.username,),
    )
    karya_saya = cursor.fetchall()

    if not karya_saya:
      st.info("Kamu belum pernah mengajukan portofolio.")
    else:
      for k_id, judul, kat, desk, link, status in karya_saya:
        ikon_status = "⏳ Pending" if status == "Pending" else "✅ Approved"
        with st.expander(f"{ikon_status} — {judul} ({kat})"):
          st.write(f"**Deskripsi:** {desk}")
          st.markdown(f"[🔗 Tautan Proyek]({link})")
          if st.button("🗑️ Hapus Karya Ini", key=f"hapus_siswa_{k_id}"):
            cursor.execute("DELETE FROM portfolios WHERE id = ?", (k_id,))
            conn.commit()
            st.warning("Karya dihapus.")
            st.rerun()
    conn.close()


# ==========================================
# HALAMAN 3: PANEL WEWENANG KHUSUS ADMIN
# ==========================================
elif menu == "Validasi Request Siswa (Admin)":
  st.title("🛡️ Panel Otoritas Admin")
  st.markdown("Tinjau dan setujui (*accept*) request portofolio dari akun siswa.")

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  tab_pending, tab_approved = st.tabs(["⏳ Request Masuk (Pending)", "✅ Sudah Disetujui (Approved)"])

  with tab_pending:
    cursor.execute(
        "SELECT id, username_pembuat, nama_siswa, judul_karya, kategori,"
        " deskripsi, link_repo FROM portfolios WHERE status = 'Pending' ORDER"
        " BY id ASC"
    )
    list_pending = cursor.fetchall()

    if not list_pending:
      st.info("Tidak ada request baru dari siswa.")
    else:
      for p_id, u_pembuat, nama, judul, kat, desk, link in list_pending:
        with st.container():
          st.subheader(f"🔹 {judul}")
          st.markdown(
              f"**Pengaju:** {nama} (`@{u_pembuat}`) | **Kategori:** `{kat}`"
          )
          st.write(desk)
          st.markdown(f"[🔗 Cek Tautan Proyek]({link})")

          col_acc, col_rej = st.columns([1, 4])
          with col_acc:
            if st.button("✅ Accept / Setujui", key=f"acc_{p_id}"):
              cursor.execute(
                  "UPDATE portfolios SET status = 'Approved' WHERE id = ?",
                  (p_id,),
              )
              conn.commit()
              st.success(f"Karya '{judul}' disetujui dan tayang di Galeri!")
              st.rerun()
          with col_rej:
            if st.button("❌ Tolak & Hapus", key=f"rej_{p_id}"):
              cursor.execute("DELETE FROM portfolios WHERE id = ?", (p_id,))
              conn.commit()
              st.error(f"Request '{judul}' ditolak dan dihapus.")
              st.rerun()
          st.markdown("---")

  with tab_approved:
    cursor.execute(
        "SELECT id, nama_siswa, judul_karya, kategori FROM portfolios WHERE"
        " status = 'Approved' ORDER BY id DESC"
    )
    list_approved = cursor.fetchall()

    if not list_approved:
      st.info("Belum ada karya yang disetujui.")
    else:
      for a_id, nama, judul, kat in list_approved:
        col_info, col_del = st.columns([4, 1])
        with col_info:
          st.write(f"**{judul}** — oleh {nama} (`{kat}`)")
        with col_del:
          if st.button("Tarik / Hapus", key=f"del_app_{a_id}"):
            cursor.execute("DELETE FROM portfolios WHERE id = ?", (a_id,))
            conn.commit()
            st.rerun()

  conn.close()
