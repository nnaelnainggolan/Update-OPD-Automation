# Notifikasi email (v2.11)

Di akhir setiap batch, program membuat ringkasan project yang **No Data**, **port kuning** (link di bawah 100 Mbps), **gagal**, atau **belum diproses**.
Ringkasan selalu disimpan di folder hasil batch (`notifikasi_gangguan.txt` dan `.json`).
Email hanya dikirim jika `notify_config.json` ada dan `enabled` bernilai true.

Screenshot setiap **No Data** (gambar yang sama dengan yang masuk ke Excel) ikut tertanam di badan email,
di bawah judul project dan jaringannya. Klik kanan pada gambar, lalu pilih *Copy image* untuk menyalinnya.

## Pasang
1. Salin `notify_config.example.json` menjadi `notify_config.json` di folder proyek.
2. Isi `username`, `from`, dan `to` (boleh lebih dari satu penerima).
3. Untuk Gmail buat **App Password**: akun Google > Keamanan > aktifkan Verifikasi 2 Langkah > Sandi aplikasi.
   Tempel 16 karakter itu ke `password` (spasi boleh). Jangan memakai password login biasa.
   Alternatif: kosongkan `password` dan atur variabel lingkungan `OPD_SMTP_PASSWORD`.
4. Tambahkan `notify_config.json` ke `.gitignore`.
5. Jalankan `06_MULTI_PROJECT.bat`. Log akhir menampilkan "Email notifikasi terkirim ke: ..." atau alasan gagalnya.

## Pengaturan
- `send_when_no_issue`: true untuk tetap mengirim email saat semua normal (bawaan false).
- `security`: `starttls` (port 587, bawaan), `ssl` (port 465), atau `none`.
- Kegagalan kirim email tidak mengubah hasil batch atau Excel.

## Port kuning
Jika port Metro atau Broadband yang dipilih berwarna **kuning** di Ruijie (legenda: 10M/100M, di bawah 100 Mbps), project itu dicatat sebagai **PORT KUNING** di email, lengkap dengan dua screenshot: deretan port beserta legenda warnanya, dan grafiknya.
Warna dibaca dari screenshot, tepat saat port diklik dan sebelum panel di-scroll. Jika sorotan port tidak ditemukan, warna tidak dibaca dan capture tetap berjalan (tercatat sebagai peringatan di log).
