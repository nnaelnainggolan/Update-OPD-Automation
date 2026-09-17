RUIJIE AUTO REPORT — TAHAP 2 / UJI SCREENSHOT LOKAL

UPDATE DARI TAHAP 1
Tutup semua browser login/recorder project ini.
Salin isi folder ruijie-auto-report dari ZIP ke folder project baru yang sama.
Pertahankan browser-profile dan .venv lokal. Jangan ubah project manual.
Jalankan 01_INSTALL.bat untuk menambah Pillow, lalu 04_UJI_CAPTURE.bat.
Jika sesi habis, gunakan 02_LOGIN.bat kemudian ulangi 04_UJI_CAPTURE.bat.

KONFIGURASI
Tenant: mmahmuda18@gmail.com (dua m di awal).
Project: 05-BAPPERIDA-PROVSU.
Device serial: H1U61QY000029, berdasarkan rekaman pengguna.
Metro: LAN5/WAN2, Description Metro Iforte.
Broadband: LAN6/WAN1, Description Broadband Nusanet.
Tesseract: gunakan instalasi yang sama dengan project manual; jika lokasinya
berbeda, ubah tesseract_command di config.json.

HASIL
Lihat captures/<tanggal_waktu>/:
- *_original.png: screenshot viewport browser utuh (tanpa bilah browser).
- *_graph.png: potongan Speed Summary, grafik dan legenda / No Data.
- run.log dan summary.json: status kedua jaringan, termasuk kegagalan.
File original yang ada tanpa graph berarti pemotongan/validasi gagal.
Semua hasil tahap ini perlu diperiksa manual, termasuk kelengkapan grafik.
Kirim run.log dan kedua gambar graph; bila gagal, kirim pesan kesalahannya.
Jangan kirim browser-profile atau rekaman login/password.

BATAS TAHAP INI
Belum menulis Excel/Drive dan belum memasang jadwal 14.00.
Tanggal kemarin-hari ini divalidasi; belum otomatis mengubah date picker
karena langkah date picker belum ada dalam rekaman. Tanggal salah -> berhenti.
Navigasi berasal dari rekaman, beberapa selector memakai urutan elemen dan
perlu pengujian langsung. Bukan hasil pengujian langsung akun Ruijie.
Description ditunggu lalu diberi waktu pemuatan tambahan; itu bukan jaminan
kesegaran grafik server. Verifikasi pemuatan akan diperkuat setelah uji ini.
No Data dicatat sebagai data grafik tidak tersedia, bukan vonis jaringan putus.
Tidak ada password disertakan dalam paket ini.
Jadwal Senin-Jumat 14.00 masih rencana, Sabtu-Minggu memakai versi manual.

Pengujian lokal: sintaks Python dan validasi tanggal benar/salah/pergantian bulan.
