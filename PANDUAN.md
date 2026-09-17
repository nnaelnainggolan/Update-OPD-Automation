# Panduan — paket lengkap v2.6 dengan dokumentasi

## Memperbarui instalasi yang sudah berhasil
1. Tutup semua proses 02, 03, 04, 05 dan browser project ini.
2. Cadangkan folder kode lama di laptop.
3. Salin file dari folder ruijie-auto-report pada ZIP ke folder project otomatis.
4. Pertahankan .venv, browser-profile, auth, captures, dan recordings lokal.
5. Pertahankan config.json lokal bila sudah disesuaikan. Config dalam ZIP adalah
   konfigurasi pengujian 05-BAPPERIDA-PROVSU.
6. Bila v2.6 sudah berhasil, instal ulang tidak diperlukan; Anda dapat menyalin
   dokumen CATATAN_PROGRES.md, PANDUAN.md, CHANGELOG.md dan README.txt saja.

## Instalasi pertama
Python 3.10+ dengan perintah py, internet, dan Tesseract diperlukan.
Ekstrak ke folder baru ruijie-auto-report, bukan ruijie-drive-v2 manual.
Jalankan 01_INSTALL.bat. Installer menyiapkan virtual environment, Playwright,
Chromium, dan Pillow. Tesseract memakai instalasi yang sudah dipakai project manual;
periksa tesseract_command di config.json bila executable tidak ditemukan.

## Cara yang sudah berhasil diuji pengguna
1. Jalankan 05_LOGIN_DAN_CAPTURE.bat.
2. Login manual dan isi CAPTCHA sendiri bila diminta.
3. Tunggu dashboard Home terbuka; biarkan browser tetap terbuka.
4. Tekan Enter DI TERMINAL 05, bukan menutup browser.
5. Jangan mengoperasikan browser selama navigasi dan pemilihan port otomatis.
6. Program mencoba memverifikasi tenant, membuka gateway, memilih kedua jaringan,
   memvalidasi tanggal dengan OCR, dan menyimpan gambar ke captures/<waktu>/.
7. Periksa gambar dan summary.json. File original saja tidak menandakan capture
   sukses jika graph belum terbentuk atau status summary adalah failed.

## Arti file hasil
- *_original.png: screenshot viewport utuh untuk jaringan tersebut.
- *_graph.png: potongan Speed Summary untuk calon laporan Excel.
- summary.json: status per jaringan; graph_present, no_data, atau failed.
- run.log: urutan proses dan pesan kesalahan.
- diagnostic.png: kondisi saat navigasi gagal.
- diagnostic_METRO/BROADBAND.png dan .txt: kondisi saat proses jaringan gagal.

## Tombol lain
- 01_INSTALL.bat: instalasi dependensi.
- 02_LOGIN.bat: login dan mencoba menyimpan sesi; pemulihan sesi belum andal.
- 03_REKAM_NAVIGASI.bat: alat rekam navigasi bila perlu memetakan tombol baru.
  Jangan merekam password/OTP. Rekaman lama pernah memuat password.
- 04_UJI_CAPTURE.bat: percobaan capture memakai sesi tersimpan; masih bermasalah
  pada pengujian pengguna. Gunakan 05 untuk alur pengujian saat ini.

## Masalah umum
- Profile already in use: tutup browser/proses project lain; hanya satu memakai profil.
- Sesi login habis: gunakan 05 dan login dalam browser yang sama.
- Tanggal tidak sesuai: tampilkan rentang kemarin-hari ini di Ruijie; program belum
  mengatur date picker otomatis dan sengaja menolak tanggal salah.
- Tombol/grafik tidak terbaca: simpan log dan gambar diagnostik; periksa sebelum dikirim.
- Jangan hapus browser-profile hanya untuk mengatasi error tanpa backup lokal.

## Status keluaran
Tidak ada penulisan Drive/Excel, pengiriman WhatsApp, atau pemasangan jadwal pada paket ini.
Jadwal dalam config adalah target pengembangan, bukan task Windows aktif.
Simpan folder auth dan browser-profile secara privat. Paket distribusi tidak menyertakannya.

## Standar setiap paket berikutnya
CATATAN_PROGRES.md harus menjelaskan fitur selesai, bukti pengujian, kendala, langkah berikutnya.
PANDUAN.md harus menjelaskan pemasangan, menjalankan, hasil, dan penanganan error.
CHANGELOG.md harus mencatat versi, perubahan, dan batas verifikasi.
Nyatakan apakah ZIP merupakan patch atau paket lengkap serta file mana yang perlu diganti.
