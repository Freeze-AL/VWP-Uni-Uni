# VWP Monitoring — Streamlit saja (tanpa Supabase)

## Upload via website GitHub
1. Buat repository **PRIVATE** di GitHub. File `monitoring.db` berisi data historis proyek; jangan upload ke repository publik.
2. Upload `app.py`, `requirements.txt`, `monitoring.db` ke root repository melalui **Add file → Upload files → Commit changes**.
3. Masuk ke https://share.streamlit.io → Create app → pilih repo, branch `main`, main file `app.py` → Deploy.
4. Buka link Streamlit dari HP. Tidak perlu Supabase, SQL, atau Secrets.
5. Gunakan menu **Backup & Restore** untuk mengunduh backup ZIP sesudah input data. Backup juga mencakup foto. Simpan backup di perangkat Anda.

## Penting
- Streamlit Community Cloud memiliki filesystem sementara. Data baru yang ditulis ke SQLite dan foto **bisa hilang** saat restart/redeploy. Backup/restore manual **wajib** untuk mencegah kehilangan data. Tidak cocok untuk penggunaan banyak petugas bersamaan atau kebutuhan penyimpanan permanen.
- Aplikasi belum memiliki login. Repository private **tidak** otomatis membuat website Streamlit private; jangan publikasikan data sensitif pada aplikasi terbuka.
- Nilai Ru = tekanan pori / sigma_v; isi `sigma_v` dalam kPa pada pengaturan instrumen. Rumus tekanan mengikuti aplikasi sebelumnya dan **perlu validasi satuan dan sertifikat kalibrasi** sebelum penggunaan teknis.
- Bila ingin data selalu tersimpan otomatis secara online, diperlukan penyimpanan persisten eksternal (misalnya Supabase) atau server sendiri dengan disk persisten.
