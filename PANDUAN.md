# v2.10.1 — 36 project

Timpa isi paket ke folder project, kemudian jalankan 06_MULTI_PROJECT.bat. Seluruh 36 project aktif; HQ hanya Metro dan tidak mencoba Broadband. Siapkan Excel tanggal laporan seperti biasa. Jika sheet 01-HQ-KOMINFO-PROVSU belum ada, sistem membuat sheet sederhana saat menyimpan capture Metro yang valid di A18; A17 berisi Link Metro. Sheet lain tetap wajib tersedia. Backup dibuat sebelum file laporan diganti. HQ yang sudah ada digunakan kembali tanpa dibuat ganda. Paket menyertakan pembaruan v2.10 sehingga boleh dipasang langsung di atas v2.9.3.

## Riwayat versi sebelumnya

# Panduan pembaruan multi-project v2.10

## Memasang
1. Tutup proses automation.
2. Cadangkan folder project yang sedang digunakan, khususnya projects.json.
3. Ekstrak isi ZIP ini langsung ke folder ruijie-auto-report dan timpa file dengan nama sama.
4. config.json, excel_config.json, browser-profile dan folder auth tidak disertakan; pengaturan milik Anda tetap digunakan.
5. Siapkan Excel tanggal laporan pada folder DRIVE_REPORT_FOLDER. Contoh tanggal 21 September: `21 SEPTEMBER 2026.xlsx`. Tutup aplikasi Excel yang membuka file tersebut.
6. Jalankan `06_MULTI_PROJECT.bat`, selesaikan login manual, lalu Enter pada dashboard.

## Cakupan
36 project terdaftar mengikuti urutan Ruijie yang dikirim pengguna. Sebanyak 34 aktif: dua pernah berhasil diuji langsung (BAPPERIDA/DINKES), 32 lainnya dipetakan dari screenshot dan masih perlu uji browser. Dua project belum diaktifkan karena bukti belum lengkap; lihat DATA_BELUM_LENGKAP.md.

Sistem memakai SN dan nomor port tetap dari projects.json. Tidak menggunakan deteksi gateway/P/S otomatis. Anda tidak perlu menjalankan 07_UJI_DETEKSI_OTOMATIS.bat.

## Sebelum browser dibuka
Program memeriksa file Excel tanggal hari ini WIB dan nama sheet semua project aktif. Jika tidak cocok, program memberi tahu nama sheet yang perlu diperiksa dan berhenti. Referensi nama sheet berasal dari template 18 September yang pernah dikirim; Excel terbaru tidak ada di ZIP screenshot. Jangan mengubah nama sheet secara acak: sesuaikan report_sheet dengan nama sebenarnya bila laporan terbaru berbeda.

## Urutan dan penyimpanan
- Ikuti project_order.json, tidak diurutkan menurut nomor depan.
- Login dan pilih tenant sekali untuk batch.
- Tiap project: buka gateway sesuai SN, ambil Metro lalu Broadband, periksa tanggal grafik kemarin sampai hari ini, simpan original dan crop.
- Metro masuk A18, Broadband A2. Slot berisi gambar dilewati tanpa ditimpa.
- No Data pada Speed Summary tetap dapat disimpan. Kegagalan membuka halaman tidak dianggap No Data.
- Excel disimpan melalui salinan lokal terverifikasi dan backup. Sinkronisasi online mengikuti Drive for Desktop.
- Bila salah satu project gagal, hasil dan diagnostik disimpan, lalu batch berhenti sebelum project berikutnya.

## Hasil dan pengujian
Hasil terdapat di captures/multi_<waktu>/<nama_project>/. Periksa summary.json, excel_result.json serta kedua gambar grafik. Log pada terminal menunjukkan urutan dan hasil. Jika gagal, kirim run.log dan diagnostic_navigation.png/.txt atau diagnostic_METRO/BROADBAND dari folder project yang gagal.

Untuk kembali menguji hanya dua project yang sudah berhasil, jalankan `08_UJI_2_PROJECT.bat` (menggunakan projects_2_verified.json). Ini tetap mode pemetaan tetap, bukan deteksi otomatis.

## Batas saat ini
- Jadwal otomatis 14:00 belum diaktifkan; login masih manual.
- DISBUN berstatus Waiting pada screenshot. Status ini tidak memastikan keadaan saat batch berjalan; jika navigasi/capture gagal batch tetap berhenti.
- Beberapa WAN tampak tidak tersambung pada screenshot; pemetaan tetap dicatat dan tidak disamakan dengan gangguan terkonfirmasi.
- Pemetaan dari screenshot tidak membuktikan semua 34 project sudah lolos pengujian browser.
