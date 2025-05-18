import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import os
from io import BytesIO
import io 
import pickle
from datetime import datetime
import openpyxl

# Fungsi simpan dan muat session state
def simpan_session_state():
    with open("session_state.pkl", "wb") as f:
        pickle.dump(dict(st.session_state), f)

def muat_session_state():
    if os.path.exists("session_state.pkl"):
        with open("session_state.pkl", "rb") as f:
            data = pickle.load(f)
            for k, v in data.items():
                if k not in st.session_state:
                    st.session_state[k] = v

# Fungsi hapus session state
def hapus_session_state_file():
    if os.path.exists("session_state.pkl"):
        os.remove("session_state.pkl")

# Fungsi ekspor ke Excel
def simpan_semua_ke_excel():
    if not st.session_state.get("jurnal"):
        return None, None
    urutkan_berdasarkan = "Tanggal"
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        
        # --- JURNAL UMUM ---
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        df_jurnal.to_excel(writer, sheet_name="Jurnal Umum", index=False)

        # --- BUKU BESAR ---
        akun_list = df_jurnal["Akun"].unique()
        buku_besar_all = []

        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            df_akun.insert(0, "Nama Akun", akun)  # Tambahkan kolom identifikasi akun
            buku_besar_all.append(df_akun)

        df_buku_besar = pd.concat(buku_besar_all, ignore_index=True)
        df_buku_besar.to_excel(writer, sheet_name="Buku Besar", index=False)

        # --- NERACA SALDO ---
        ref_dict = df_jurnal.groupby("Akun")["Ref"].first().to_dict()

        neraca_saldo = df_jurnal.groupby("Akun")[["Debit", "Kredit"]].sum().reset_index()
        neraca_saldo["Saldo"] = neraca_saldo["Debit"] - neraca_saldo["Kredit"]
        neraca_saldo["Ref"] = neraca_saldo["Akun"].map(ref_dict)
        neraca_saldo = neraca_saldo.sort_values(by="Ref")
        cols = ["Ref", "Akun", "Debit", "Kredit", "Saldo"]
        neraca_saldo = neraca_saldo[cols]
        neraca_saldo.to_excel(writer, sheet_name="Neraca Saldo", index=False)
        
        # --- LABA RUGI ---
        if "data_laba_rugi" in st.session_state:
            laba_rugi_all = []
            for kategori, data in st.session_state.data_laba_rugi.items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df.insert(0, "Kategori", kategori)
                    laba_rugi_all.append(df)

            if laba_rugi_all:
                df_laba_rugi = pd.concat(laba_rugi_all, ignore_index=True)
                total_pendapatan = df_laba_rugi[df_laba_rugi["Kategori"] == "Pendapatan"]["Nominal"].sum()
                total_beban = df_laba_rugi[df_laba_rugi["Kategori"] != "Pendapatan"]["Nominal"].sum()
                laba_bersih = total_pendapatan - total_beban
                df_laba_bersih = pd.DataFrame([{
                    "Kategori": "",
                    "Deskripsi": "Laba/Rugi Bersih",
                    "Nominal": laba_bersih
                }])
                df_output = pd.concat([df_laba_rugi, pd.DataFrame([{}]), df_laba_bersih], ignore_index=True)
                df_output.to_excel(writer, sheet_name="Laporan Laba Rugi", index=False)

        # --- PERUBAHAN EKUITAS ---
        if (
            st.session_state.get("modal_awal") is not None and
            st.session_state.get("laba") is not None and
            st.session_state.get("prive") is not None
        ):
            ekuitas_akhir = (
                st.session_state.modal_awal +
                st.session_state.laba -
                st.session_state.prive
            )
            df_ekuitas = pd.DataFrame([{
                "Modal Awal": st.session_state.modal_awal,
                "Laba": st.session_state.laba,
                "Prive": st.session_state.prive,
                "Ekuitas Akhir": ekuitas_akhir
            }])
            df_ekuitas.to_excel(writer, sheet_name="Perubahan Ekuitas", index=False)

        # --- NERACA (Laporan Posisi Keuangan) ---
        if "neraca" in st.session_state:
            all_data = []
            for kategori, data in st.session_state.neraca.items():
                df = pd.DataFrame(data)
                if not df.empty:
                    df['Kategori'] = kategori  # Tambahkan kolom kategori
                    all_data.append(df)

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df.to_excel(writer, sheet_name="Neraca", index=False)

    buffer.seek(0)
    filename = "laporan_keuangan_zaki_telor.xlsx"
    return buffer, filename

# Muat session state
muat_session_state()

# --- LOGIN PAGE ---
def login_page():
    if "login_success" not in st.session_state:
        st.session_state.login_success = False
    if "show_login_success" not in st.session_state:
        st.session_state.show_login_success = False

    if not st.session_state.login_success:
        st.title("🔐 Login - Zaki Telor")

        with st.form("login_form"):
            username = st.text_input("Nama Akun")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                # Autentikasi
                if username == "admin" and password == "zakitelor":
                    st.session_state.login_success = True
                    st.session_state.username = username
                    st.session_state.show_login_success = True 
                    st.rerun()
                else:
                    st.error("Nama akun atau password salah!")

    # Tampilkan notifikasi sekali setelah login
    elif st.session_state.show_login_success:
        st.success(f"Login berhasil! Selamat datang, {st.session_state.username} 👋")
        st.session_state.show_login_success = False 

    return st.session_state.login_success

# Panggil fungsi login sebelum melanjutkan
if not login_page():
    st.stop()  # Hentikan app jika belum login

# Sidebar dengan Option Menu
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>LAPORAN KEUANGAN<br>ZAKI TELOR🐔🪺</h2>", unsafe_allow_html=True)
    selected = st.sidebar.radio(
        "Navigasi",
        ["📍 Beranda", "📅 Jurnal Umum", "📓 Buku Besar", "⚖️ Neraca Saldo",
            "📈 Laporan Laba Rugi", "📊 Laporan Perubahan Ekuitas",
            "📄 Laporan Posisi Keuangan", "📥 Unduh Data"])

if selected == "📍 Beranda":
    st.title("💰LAPORAN KEUANGAN ZAKI TELOR 🐔")
    st.markdown("""
        ### Tentang Aplikasi
        Aplikasi ini dirancang untuk membantu dalam mencatat dan menyusun laporan keuangan secara praktis dan efisien.
        Fitur yang dapat dikelola antara lain:
        - Jurnal Umum
        - Buku Besar
        - Neraca Saldo
        - Laporan Laba Rugi
        - Perubahan Ekuitas
        - Laporan Posisi Keuangan (Neraca)

        ### Panduan Penggunaan
        1. Masukkan transaksi pada menu *Jurnal Umum*.
        2. Data akan otomatis terintegrasi ke *Buku Besar* dan *Neraca Saldo*.
        3. Untuk menyusun laporan laba rugi, perubahan ekuitas dan neraca, gunakan fitur input manual.
        4. Tekan tombol reset di tiap halaman untuk memulai pengisian data baru.

        ### Catatan
        - Pastikan setiap entri jurnal *seimbang* (total debit = total kredit).
        - Pastikan menginput dengan teliti dan cek secara berkala.
    """)

    st.info("Gunakan menu di sidebar untuk mulai mencatat dan melihat laporan keuangan Anda.")

# --- JURNAL UMUM ---
if selected == "📅 Jurnal Umum":
    st.header("📅 Jurnal Umum")
    if "jurnal" not in st.session_state:
        st.session_state.jurnal = []

    with st.form("form_jurnal"):
        st.subheader("Input Transaksi Jurnal")
        tanggal = st.date_input("Tanggal", value=datetime.today())
        keterangan = st.text_input("Akun")
        akun = st.text_input("Ref")
        col1, col2 = st.columns(2)
        with col1:
            debit = st.number_input("Debit (Rp)", min_value=0.0, format="%.2f")
        with col2:
            kredit = st.number_input("Kredit (Rp)", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Tambah")

        if submitted:
            if akun:
                st.session_state.jurnal.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Akun": keterangan,
                    "Ref": akun,
                    "Debit": debit,
                    "Kredit": kredit
                })
                simpan_session_state()
            else:
                st.warning("Nama akun tidak boleh kosong!")

    if st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        st.dataframe(df_jurnal, use_container_width=True)
        st.subheader("Edit Jurnal Jika Perlu:")
        df_edit = st.data_editor(df_jurnal, num_rows="dynamic", use_container_width=True, key="edit_jurnal")
        if st.button("Simpan Perubahan Jurnal"):
            st.session_state.jurnal = df_edit.to_dict(orient="records")
            simpan_session_state()
            st.success("Perubahan jurnal berhasil disimpan.")
        total_debit = df_jurnal["Debit"].sum()
        total_kredit = df_jurnal["Kredit"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Debit", f"Rp {total_debit:,.2f}")
        col2.metric("Total Kredit", f"Rp {total_kredit:,.2f}")
        if total_debit == total_kredit:
            st.success("✅ Jurnal seimbang!")
        else:
            st.error("❌ Jurnal tidak seimbang!")

    if st.button("Reset Semua Data"):
        st.session_state.jurnal = []
        hapus_session_state_file()
        st.success("Data jurnal berhasil direset.")
        st.rerun()

# --- BUKU BESAR ---
elif selected == "📓 Buku Besar":
    st.header("📓 Buku Besar")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        akun_list = df_jurnal["Akun"].unique()

        for akun in akun_list:
            st.subheader(f"Akun: {akun}")
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()

            st.dataframe(df_akun[["Tanggal", "Akun", "Debit", "Kredit", "Saldo Akumulatif"]], use_container_width=True)
            saldo_akhir = df_akun["Saldo Akumulatif"].iloc[-1]
            st.info(f"Saldo akhir akun {akun}: {saldo_akhir:,.2f}")
    else:
        st.info("Tidak ada data jurnal untuk ditampilkan di buku besar.")

# --- NERACA SALDO ---
elif selected == "⚖️ Neraca Saldo":
    st.header("⚖️ Neraca Saldo")

    if "jurnal" in st.session_state and st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal).sort_values(by=["Ref", "Tanggal"])

        # Menghitung saldo akumulatif terakhir per akun
        akun_list = df_jurnal["Akun"].unique()
        saldo_akhir_list = []

        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            saldo_akhir = df_akun["Saldo Akumulatif"].iloc[-1]
            ref = df_akun["Ref"].iloc[0]

            # Bagi ke debit/kredit sesuai saldo
            debit = saldo_akhir if saldo_akhir >= 0 else 0
            kredit = -saldo_akhir if saldo_akhir < 0 else 0
            saldo_akhir_list.append({
                "Ref": ref,
                "Akun": akun,
                "Debit": debit,
                "Kredit": kredit
            })

        df_saldo = pd.DataFrame(saldo_akhir_list)
        df_saldo = df_saldo.sort_values(by="Ref")
        total_debit = df_saldo["Debit"].sum()
        total_kredit = df_saldo["Kredit"].sum()
        total_row = pd.DataFrame({
            "Ref": ["TOTAL"],
            "Akun": [""],
            "Debit": [total_debit],
            "Kredit": [total_kredit]
        })

        df_saldo_tampil = pd.concat([df_saldo, total_row], ignore_index=True)
        st.dataframe(df_saldo_tampil[["Ref", "Akun", "Debit", "Kredit"]], use_container_width=True)

        if total_debit == total_kredit:
            st.success("✅ Neraca Saldo Seimbang")
        else:
            st.error(f"❌ Neraca Saldo Tidak Seimbang — Selisih: Rp {abs(total_debit - total_kredit):,.2f}")

    else:
        st.info("Belum ada data jurnal untuk dihitung.")

# --- LABA RUGI ---
elif selected == "📈 Laporan Laba Rugi":
    st.header("📈 Laporan Laba Rugi")
    kategori_list = ["Pendapatan", "Beban Listrik", "Beban Air", "Beban Perawatan"]
    if "data_laba_rugi" not in st.session_state:
        st.session_state.data_laba_rugi = {kategori: [] for kategori in kategori_list}

    tab1, tab2 = st.tabs(["Input Transaksi", "Laporan Laba Rugi"])

    with tab1:
        kategori = st.selectbox("Kategori", kategori_list)
        deskripsi = st.text_input("Deskripsi")
        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown("**Rp**")
        with col2:
            nominal = st.number_input("Nominal", min_value=0, step=1000)
        if st.button("Tambah Transaksi"):
            if deskripsi and nominal > 0:
                st.session_state.data_laba_rugi[kategori].append({"Deskripsi": deskripsi, "Nominal": nominal})
                st.success(f"{kategori} berhasil ditambahkan.")
                simpan_session_state()
            else:
                st.warning("Mohon isi deskripsi dan nominal dengan benar.")

    with tab2:
        total_pendapatan = sum(item["Nominal"] for item in st.session_state.data_laba_rugi["Pendapatan"])
        total_beban = 0
        for kategori in kategori_list[1:]:
            df = pd.DataFrame(st.session_state.data_laba_rugi[kategori])
            subtotal = df["Nominal"].sum() if not df.empty else 0
            total_beban += subtotal
            st.subheader(kategori)
            if not df.empty:
                df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{kategori}")
                if st.button(f"Simpan Perubahan {kategori}"):
                    st.session_state.data_laba_rugi[kategori] = df_edit.to_dict(orient="records")
                    simpan_session_state()
                    st.success(f"Perubahan {kategori} berhasil disimpan.")
            st.write(f"Total {kategori}: Rp {subtotal:,.0f}")

        st.subheader("Pendapatan")
        df_pendapatan = pd.DataFrame(st.session_state.data_laba_rugi["Pendapatan"])
        if not df_pendapatan.empty:
            df_edit = st.data_editor(df_pendapatan, num_rows="dynamic", use_container_width=True, key="edit_pendapatan")
            if st.button("Simpan Perubahan Pendapatan"):
                st.session_state.data_laba_rugi["Pendapatan"] = df_edit.to_dict(orient="records")
                simpan_session_state()
                st.success("Perubahan pendapatan berhasil disimpan.")
        else:
            st.dataframe(pd.DataFrame(columns=["Deskripsi", "Nominal"]))

        laba_rugi = total_pendapatan - total_beban
        st.metric("Laba / Rugi Bersih", f"Rp {laba_rugi:,.0f}")

        if st.button("Reset Semua Data", key="reset_button_1"):
            st.session_state.data_laba_rugi = {kategori: [] for kategori in kategori_list}
            hapus_session_state_file()
            st.success("Data laba rugi berhasil direset.")

# --- PERUBAHAN EKUITAS ---
elif selected == "📊 Laporan Perubahan Ekuitas":
    st.header("📊 Laporan Perubahan Ekuitas")

    # Inisialisasi jika belum ada
    if "modal_awal" not in st.session_state:
        st.session_state.modal_awal = None
    if "laba" not in st.session_state:
        st.session_state.laba = None
    if "prive" not in st.session_state:
        st.session_state.prive = None

    # Jika belum ada data, gunakan input biasa
    if st.session_state.modal_awal is None or st.session_state.laba is None or st.session_state.prive is None:
        st.subheader("Input Ekuitas")
        col1, col2 = st.columns([1, 5])
        with col1: st.markdown("**Modal Awal** (Rp)")
        with col2: modal_awal = st.number_input("", min_value=0, step=1000, key="modal_awal_input")

        col1, col2 = st.columns([1, 5])
        with col1: st.markdown("**Laba** (Rp)")
        with col2: laba = st.number_input("", min_value=0, step=1000, key="laba_input")

        col1, col2 = st.columns([1, 5])
        with col1: st.markdown("**Prive** (Rp)")
        with col2: prive = st.number_input("", min_value=0, step=1000, key="prive_input")

        if st.button("Simpan Data"):
            st.session_state.modal_awal = modal_awal
            st.session_state.laba = laba
            st.session_state.prive = prive
            simpan_session_state()
            st.success("Data berhasil disimpan.")
    else:
        st.subheader("Edit Data Ekuitas")
        df_ekuitas = pd.DataFrame([{
            "Modal Awal": st.session_state.modal_awal,
            "Laba": st.session_state.laba,
            "Prive": st.session_state.prive
        }])
        df_edit = st.data_editor(df_ekuitas, num_rows=1, use_container_width=True, key="edit_ekuitas")
        if st.button("Simpan Perubahan Ekuitas"):
            st.session_state.modal_awal = df_edit["Modal Awal"].iloc[0]
            st.session_state.laba = df_edit["Laba"].iloc[0]
            st.session_state.prive = df_edit["Prive"].iloc[0]
            simpan_session_state()
            st.success("Perubahan ekuitas berhasil disimpan.")

    # Menampilkan laporan
    if st.session_state.modal_awal is not None:
        ekuitas_akhir = st.session_state.modal_awal + st.session_state.laba - st.session_state.prive
        st.subheader("Laporan Perubahan Ekuitas")
        st.write(f"Modal Awal: Rp {st.session_state.modal_awal:,.0f}")
        st.write(f"Tambah: Laba Bersih: Rp {st.session_state.laba:,.0f}")
        st.write(f"Kurang: Prive: Rp {st.session_state.prive:,.0f}")
        st.metric("Ekuitas Akhir", f"Rp {ekuitas_akhir:,.0f}")

    if st.button("Reset Data"):
        st.session_state.modal_awal = None
        st.session_state.laba = None
        st.session_state.prive = None
        simpan_session_state()
        st.success("Data berhasil direset.")

# --- NERACA (POSISI KEUANGAN) ---
elif selected == "📄 Laporan Posisi Keuangan":
    st.header("📄 Laporan Posisi Keuangan")

    struktur = {"Aktiva Lancar": [], "Aktiva Tetap": [], "Kewajiban": [], "Ekuitas": []}
    if "neraca" not in st.session_state:
        st.session_state.neraca = {kategori: [] for kategori in struktur}

    tab1, tab2 = st.tabs(["Input Manual", "Laporan Posisi Keuangan"])

    # Tab Input Manual
    with tab1:
        kategori = st.selectbox("Kategori", list(st.session_state.neraca.keys()))
        nama_akun = st.text_input("Nama Akun")
        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown("**Rp**")
        with col2:
            nilai = st.number_input("Nilai", min_value=0, step=1000)

        if st.button("Tambah Akun"):
            if nama_akun and nilai > 0:
                st.session_state.neraca[kategori].append({"Akun": nama_akun, "Nilai": nilai})
                simpan_session_state()
                st.success(f"{nama_akun} berhasil ditambahkan ke {kategori}.")
            else:
                st.warning("Harap isi nama akun dan nilai yang valid.")

    # Tab Laporan Posisi Keuangan (dengan editor)
    with tab2:
        col1, col2 = st.columns(2)
        total_aktiva = 0

        with col1:
            st.subheader("Aktiva")
            for kategori in ["Aktiva Lancar", "Aktiva Tetap"]:
                st.markdown(f"### {kategori}")
                df = pd.DataFrame(st.session_state.neraca[kategori])
                if not df.empty:
                    df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{kategori}")
                    if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_{kategori}"):
                        st.session_state.neraca[kategori] = df_edit.to_dict(orient="records")
                        simpan_session_state()
                        st.success(f"Perubahan {kategori} berhasil disimpan.")
                    subtotal = df_edit["Nilai"].sum()
                    total_aktiva += subtotal
                    st.write(f"Subtotal {kategori}: Rp {subtotal:,.0f}")
                else:
                    st.info(f"Tidak ada data untuk {kategori}")
            st.markdown(f"**Total Aktiva: Rp {total_aktiva:,.0f}**")

        total_pasiva = 0
        with col2:
            st.subheader("Pasiva")
            for kategori in ["Kewajiban", "Ekuitas"]:
                st.markdown(f"### {kategori}")
                df = pd.DataFrame(st.session_state.neraca[kategori])
                if not df.empty:
                    df_edit = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{kategori}")
                    if st.button(f"Simpan Perubahan {kategori}", key=f"simpan_{kategori}"):
                        st.session_state.neraca[kategori] = df_edit.to_dict(orient="records")
                        simpan_session_state()
                        st.success(f"Perubahan {kategori} berhasil disimpan.")
                    subtotal = df_edit["Nilai"].sum()
                    total_pasiva += subtotal
                    st.write(f"Subtotal {kategori}: Rp {subtotal:,.0f}")
                else:
                    st.info(f"Tidak ada data untuk {kategori}")
            st.markdown(f"**Total Pasiva: Rp {total_pasiva:,.0f}**")

        # Validasi neraca
        if total_aktiva == total_pasiva:
            st.success("✅ Neraca Seimbang")
        else:
            st.error(f"Selisih Neraca: Rp {abs(total_aktiva - total_pasiva):,.0f}")

        # Tombol reset
        if st.button("Reset Semua Data", key="reset_button_2"):
            st.session_state.neraca = {kategori: [] for kategori in struktur}
            simpan_session_state()
            st.success("Semua data berhasil direset.")

# --- UNDUH DATA ---
elif selected == "📥 Unduh Data":
    st.title("📥 Unduh Laporan Keuangan")

    if st.button("Simpan ke Excel"):
        excel_io, filename = simpan_semua_ke_excel()
        if excel_io:
            st.session_state.excel_io = excel_io
            st.session_state.excel_filename = filename
            st.success("File berhasil dibuat, silakan unduh di bawah.")
        else:
            st.warning("Tidak ada data jurnal untuk disimpan.")

    if "excel_io" in st.session_state and "excel_filename" in st.session_state:
        st.download_button(
            label="📥",
            data=st.session_state.excel_io,
            file_name=st.session_state.excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Klik tombol 'Simpan ke Excel' terlebih dahulu untuk membuat file.")