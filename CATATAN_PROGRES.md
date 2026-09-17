# Catatan progres — Ruijie Auto Report

Diperbarui: 17 September 2026. Dasar kode: v2.6.
Paket ini menggabungkan kode tahap 1, tahap 2, dan patch hingga v2.6.
Pembaruan kali ini hanya melengkapi dokumentasi, bukan menambah fitur otomatisasi.

## Tujuan dan keputusan
- Project otomatis terpisah dari project manual ruijie-drive-v2.
- Target akhir: 36 project, Senin–Jumat pukul 14.00 WIB.
- Sabtu–Minggu dikerjakan dengan project screenshot manual.
- Rentang grafik: kemarin sampai hari ini; file Excel memakai tanggal akhir.
- Excel hanya ditambah gambar. Broadband A2, Metro A18.
- Screenshot asli tetap disimpan; gambar laporan dipotong dari judul Speed Summary
  sampai legenda Uplink/Downlink, atau area No Data pada bagian tersebut.
- No Data pada DNS/Link Probe tidak dianggap No Data Speed Summary.
- WhatsApp dikirim manual; tidak memakai n8n atau pengiriman otomatis.
- Pengembangan berikutnya memakai file Excel pengujian, bukan laporan asli.

## Sudah berhasil
- Versi manual terpisah sudah berjalan; pembaruan terakhir v16 mengurutkan popup
  ke bawah lalu ke kolom kanan dan mendukung sheet HQ otomatis setelah konfirmasi.
- Versi otomatis: login manual di browser khusus, dilanjutkan capture di browser yang sama.
- Pindah tenant dari akun awal ke mmahmuda18@gmail.com.
- Membuka 05-BAPPERIDA-PROVSU dan gateway H1U61QY000029.
- Memilih Metro LAN5/WAN2 dan Broadband LAN6/WAN1.
- OCR tanggal dan pemotongan grafik serta pemisahan bagian Link/DNS Probe.
- Pengguna mengirim empat hasil asli/graph pada 17 September 2026:
  kedua grafik lengkap, rentang 16–17 September 2026, jaringan sesuai.

## Belum selesai
- Penulisan hasil otomatis ke Excel: belum diimplementasikan pada project ini.
- Pemetaan dan navigasi seluruh 36 project: baru satu project diuji.
- Pemulihan sesi login tanpa pendampingan: belum berhasil andal.
- Pemilihan rentang tanggal otomatis: belum ada; tanggal hanya divalidasi.
- Jadwal Windows pukul 14.00: belum dipasang. config hanya berisi rencana.
- Validasi kesegaran grafik server dan retry No Data: perlu diperkuat.
- Pemulihan kegagalan, ringkasan harian seluruh project dan uji end-to-end: belum selesai.

## Konfigurasi pengujian yang disepakati
- Tenant: mmahmuda18@gmail.com (dua m di awal).
- Project Ruijie: 05-BAPPERIDA-PROVSU.
- Tujuan sheet yang direncanakan: 05-BAPPELITBANG-PROVSU.
- Gateway serial: H1U61QY000029.
- Metro: LAN5/WAN2; Description Metro Iforte.
- Broadband: LAN6/WAN1; Description Broadband Nusanet.
- Lokasi project terakhir di laptop: D:\MAGANG\OPD auto report\ruijie-auto-report.

## Batas teknis saat ini
- Jalur yang berhasil memakai 05_LOGIN_DAN_CAPTURE.bat dan login manual.
- Sesi tersimpan belum berarti sesi dapat dipakai ulang oleh 04_UJI_CAPTURE.bat.
- Pembuka avatar memakai posisi yang diverifikasi pada viewport 1440px.
- Beberapa selector project mengikuti urutan elemen dari rekaman pengguna.
- Screenshot asli adalah viewport halaman, bukan seluruh halaman panjang atau desktop.
- Ikon asisten Ruijie masih terlihat pada sisi kanan hasil crop.
- Grafik terdeteksi bukan bukti jaringan selalu sehat; No Data bukan bukti pasti putus.

## Langkah berikutnya
1. Buat integrasi dengan Excel pengujian untuk dua gambar yang berhasil.
2. Uji A2/A18, pemetaan sheet, backup, duplikat, dan laporan tanggal salah.
3. Petakan gateway/port/nama sheet untuk project lain dan uji bertahap.
4. Selesaikan autentikasi untuk jadwal tanpa pendampingan.
5. Pasang dan uji Windows Task Scheduler Senin–Jumat 14.00 WIB.

## Melanjutkan percakapan
Kirim paket kode terbaru, file ini, dan log kegagalan terakhir (jika ada).
Jangan kirim folder auth, browser-profile, password, atau token sesi.
Jangan menyatakan jadwal/login otomatis/Excel sudah selesai sebelum diuji.
