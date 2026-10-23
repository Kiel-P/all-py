import requests
import json
import sys
import os

# Kode Warna ANSI untuk Terminal
class Warna:
    CYAN = '\033[96m'
    HIJAU = '\033[92m'
    KUNING = '\033[93m'
    MERAH = '\033[91m'
    BIRU = '\033[94m'
    RESET = '\033[0m'
    TEBAL = '\033[1m'

def bersihkan_layar():
    os.system('clear' if os.name == 'posix' else 'cls')

def tampilkan_header():
    bersihkan_layar()
    print(f"{Warna.CYAN}{Warna.TEBAL}╔════════════════════════════════════════════════════════════╗{Warna.RESET}")
    print(f"{Warna.CYAN}{Warna.TEBAL}║                  TERMINAL AI CHAT (PRO)                    ║{Warna.RESET}")
    print(f"{Warna.CYAN}{Warna.TEBAL}╚════════════════════════════════════════════════════════════╝{Warna.RESET}")
    print(f"{Warna.KUNING}Perintah Tersedia:{Warna.RESET}")
    print(f" {Warna.HIJAU}keluar{Warna.RESET}  : Menghentikan aplikasi")
    print(f" {Warna.HIJAU}clear{Warna.RESET}   : Membersihkan layar terminal")
    print(f" {Warna.HIJAU}/model{Warna.RESET}  : Mengganti model AI tanpa keluar aplikasi")
    print(f" {Warna.HIJAU}/reset{Warna.RESET}  : Menghapus ingatan/riwayat chat AI\n")

# --- SETUP KREDENSIAL ---
bersihkan_layar()
print(f"{Warna.CYAN}{Warna.TEBAL}=== PENGATURAN API SERVER ==={Warna.RESET}")
print(f"{Warna.KUNING}Tekan Enter langsung jika ingin menggunakan Base URL bawaan.{Warna.RESET}")

default_url = "https://bansos.adiosverm.eu.cc/v1"
input_url = input(f"Base URL [{default_url}]: ").strip()
BASE_URL = input_url if input_url else default_url

API_KEY = input("API Key  : ").strip()
while not API_KEY:
    print(f"{Warna.MERAH}[!] API Key tidak boleh kosong!{Warna.RESET}")
    API_KEY = input("API Key  : ").strip()

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- SETUP MODEL ---
print(f"\nCek model aktif di: {Warna.BIRU}monitor.adiosverm.eu.cc{Warna.RESET}")
model_name = input(f"{Warna.TEBAL}Masukkan Nama Model API : {Warna.RESET}").strip()
while not model_name:
    model_name = input(f"{Warna.TEBAL}Masukkan Nama Model API : {Warna.RESET}").strip()

history = []
tampilkan_header()
print(f"{Warna.HIJAU}[✓] Terhubung ke URL : {Warna.TEBAL}{BASE_URL}{Warna.RESET}")
print(f"{Warna.HIJAU}[✓] Model saat ini   : {Warna.TEBAL}{model_name}{Warna.RESET}")
print(f"{Warna.CYAN}──────────────────────────────────────────────────────────────{Warna.RESET}")

# --- LOOP CHAT ---
while True:
    try:
        user_text = input(f"\n{Warna.HIJAU}{Warna.TEBAL}Anda  ❯ {Warna.RESET}").strip()
        
        # Cek perintah sistem
        if user_text.lower() in ['keluar', 'exit', 'quit']:
            print(f"\n{Warna.KUNING}Menutup sesi chat. Sampai jumpa!{Warna.RESET}\n")
            break
        elif user_text.lower() == 'clear':
            tampilkan_header()
            print(f"{Warna.HIJAU}[✓] Terhubung ke URL : {Warna.TEBAL}{BASE_URL}{Warna.RESET}")
            print(f"{Warna.HIJAU}[✓] Model saat ini   : {Warna.TEBAL}{model_name}{Warna.RESET}")
            print(f"{Warna.CYAN}──────────────────────────────────────────────────────────────{Warna.RESET}")
            continue
        elif user_text.lower() == '/model':
            print(f"\n{Warna.KUNING}>> Ganti Model AI{Warna.RESET}")
            new_model = input("Masukkan Nama Model Baru: ").strip()
            if new_model:
                model_name = new_model
                print(f"{Warna.HIJAU}[✓] Model berhasil diganti ke: {Warna.TEBAL}{model_name}{Warna.RESET}")
            else:
                print(f"{Warna.MERAH}[!] Batal mengganti model.{Warna.RESET}")
            continue
        elif user_text.lower() == '/reset':
            history = []
            print(f"\n{Warna.HIJAU}[✓] Ingatan chat berhasil dihapus. AI siap memulai percakapan baru.{Warna.RESET}")
            continue
        elif not user_text:
            continue

        history.append({"role": "user", "content": user_text})
        payload = {"model": model_name, "messages": history}

        sys.stdout.write(f"{Warna.KUNING}Memproses respons dari server...{Warna.RESET}\r")
        sys.stdout.flush()

        response = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload)
        sys.stdout.write('\033[K') # Hapus teks loading
        
        try:
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                
                if "Your quota is exhausted" in reply or "API key status: exceeded" in reply:
                    print(f"\n{Warna.MERAH}{Warna.TEBAL}SISTEM ❯ {Warna.RESET}{Warna.MERAH}Peringatan: Kuota API Key telah habis.{Warna.RESET}")
                    print(f"         {Warna.CYAN}Pesan Server Asli:{Warna.RESET}\n         {reply.replace(chr(10), chr(10)+'         ')}")
                    history.pop()
                else:
                    print(f"\n{Warna.CYAN}{Warna.TEBAL}AI    ❯ {Warna.RESET}{reply}")
                    history.append({"role": "assistant", "content": reply})
                    
            elif "error" in data:
                # Ekstrak pesan error agar lebih rapi seperti di tangkapan layarmu
                err_msg = data['error']['message'] if isinstance(data['error'], dict) and 'message' in data['error'] else data['error']
                print(f"\n{Warna.MERAH}{Warna.TEBAL}ERROR ❯ {Warna.RESET}{err_msg}")
                history.pop()
            else:
                print(f"\n{Warna.MERAH}{Warna.TEBAL}SYSTEM ❯ {Warna.RESET}Format respons tidak dikenal.")
                history.pop()
                
        except requests.exceptions.JSONDecodeError:
            print(f"\n{Warna.MERAH}{Warna.TEBAL}GAGAL ❯ {Warna.RESET}Koneksi ditolak oleh server (Status: {response.status_code})")
            history.pop()

    except KeyboardInterrupt:
        print(f"\n\n{Warna.MERAH}[!] Program dihentikan paksa (Ctrl+C).{Warna.RESET}")
        break
    except Exception as e:
        sys.stdout.write('\033[K') 
        print(f"\n{Warna.MERAH}{Warna.TEBAL}KONEKSI ❯ {Warna.RESET}Terjadi kesalahan jaringan ({e})")
        if len(history) > 0:
            history.pop()
