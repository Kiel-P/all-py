import concurrent.futures
from datetime import datetime
import json
import os
import re
import urllib.request
from tqdm import tqdm

CREATED_BY = "K I H E O"


def parse_proxy_line(line):
    line = line.strip()
    if not line:
        return None

    if "," in line:
        parts = [p.strip() for p in line.split(",", 3)]
        if len(parts) >= 2:
            ip = parts[0]
            port = parts[1]
            country = parts[2] if len(parts) > 2 and parts[2] else None
            isp = parts[3] if len(parts) > 3 and parts[3] else None
            is_ipv6 = ":" in ip and not ip.startswith("[")
            display_ip = f"[{ip}]" if is_ipv6 else ip
            return {
                "raw_ip": ip.replace("[", "").replace("]", ""),
                "port": port,
                "display_ip": display_ip,
                "is_ipv6": is_ipv6,
                "preset_country": country,
                "preset_isp": isp,
            }

    ipv6_match = re.match(r"^\[([a-fA-F0-9:]+)\]:(\d+)$", line)
    if ipv6_match:
        return {
            "raw_ip": ipv6_match.group(1),
            "port": ipv6_match.group(2),
            "display_ip": f"[{ipv6_match.group(1)}]",
            "is_ipv6": True,
            "preset_country": None,
            "preset_isp": None,
        }

    ipv4_match = re.match(r"^([0-9\.]+):(\d+)$", line)
    if ipv4_match:
        return {
            "raw_ip": ipv4_match.group(1),
            "port": ipv4_match.group(2),
            "display_ip": ipv4_match.group(1),
            "is_ipv6": False,
            "preset_country": None,
            "preset_isp": None,
        }

    return None


def get_geoip_info(ip):
    try:
        url = f"http://ip-api.com/json/{ip}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                return (
                    data.get("countryCode", "XX"),
                    data.get("city", "N/A"),
                    data.get("isp", "Unknown ISP"),
                )
    except Exception:
        pass
    return "XX", "N/A", "Unknown ISP"


def check_vless_proxy(proxy_data, timeout=3):
    """Fungsi ini mengetes apakah Proxy IP benar-benar bisa meneruskan trafik WebSocket (VLESS/Trojan)"""
    if not proxy_data:
        return None

    ip_raw = proxy_data["raw_ip"]
    port = proxy_data["port"]
    display_ip = proxy_data["display_ip"]

    # Mengetes koneksi Reverse Proxy ke Cloudflare CDN
    test_url = f"http://{display_ip}:{port}/"
    headers = {
        "Host": "speed.cloudflare.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Connection": "Upgrade",
        "Upgrade": "websocket",
    }

    try:
        req = urllib.request.Request(test_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            # Menerima status 101 (Switching Protocols), 200, 100, atau 400 khusus response CDN Proxy
            if status_code in [101, 200, 100, 400, 403]:
                country = proxy_data["preset_country"]
                isp = proxy_data["preset_isp"]
                city = "N/A"

                if not country or not isp:
                    geo_country, geo_city, geo_isp = get_geoip_info(ip_raw)
                    country = country if country else geo_country
                    isp = isp if isp else geo_isp
                    city = geo_city

                proxy_addr = f"{display_ip}:{port}"
                csv_format = f"{display_ip},{port},{country},{isp}"

                return {
                    "proxy": proxy_addr,
                    "country": country,
                    "city": city,
                    "isp": isp,
                    "csv_format": csv_format,
                }
    except urllib.error.HTTPError as e:
        # Beberapa Proxy IP merespons 400 Bad Request / 101 WebSocket Upgrade saat dites header Cloudflare
        if e.code in [101, 400, 403]:
            country = proxy_data["preset_country"]
            isp = proxy_data["preset_isp"]
            city = "N/A"

            if not country or not isp:
                geo_country, geo_city, geo_isp = get_geoip_info(ip_raw)
                country = country if country else geo_country
                isp = isp if isp else geo_isp
                city = geo_city

            proxy_addr = f"{display_ip}:{port}"
            csv_format = f"{display_ip},{port},{country},{isp}"

            return {
                "proxy": proxy_addr,
                "country": country,
                "city": city,
                "isp": isp,
                "csv_format": csv_format,
            }
    except Exception:
        pass

    return None


def run_checker(raw_lines):
    parsed_list = [
        parse_proxy_line(line) for line in raw_lines if parse_proxy_line(line)
    ]
    total = len(parsed_list)

    if total == 0:
        print("\n❌ Tidak ada IP/proxy berformat valid yang bisa diproses.")
        return

    print(
        f"\n⏳ Memulai pengecekan proxy. {total} IP...\n"
    )

    live_results = []

    with tqdm(
        total=total,
        desc="Mengecek Proxy WS",
        unit="proxy",
        ncols=75,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    ) as pbar:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=25
        ) as executor:
            futures = [
                executor.submit(check_vless_proxy, p) for p in parsed_list
            ]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    live_results.append(res)
                pbar.update(1)

    live_results.sort(key=lambda x: (x["country"], x["proxy"]))

    now = datetime.now()
    time_str = now.strftime("%H:%M:%S WIB")
    date_str = now.strftime("%d %B %Y")

    print("\n" + "=" * 50)
    print("📊 HASIL CHECK PROXY")
    print("===================================")

    if live_results:
        for item in live_results:
            print(f"✅ LIVE ➔ {item['proxy']}")
            print(f"🏳️ Negara: {item['country']}")
            print(f"🏙️ City: {item['city']}")
            print(f"🏢 ISP: {item['isp']}\n")
    else:
        print("❌ Tidak ada proxy yang LIVE.\n")

    print("-----------------------------------")
    print(f"📊 Total LIVE: {len(live_results)}/{total}")
    print(f"⏰ time : {time_str}")
    print(f"📅 date : {date_str}")
    print(f"✍️ created by : {CREATED_BY}")
    print("===================================\n")

    if live_results:
        print("=" * 50)
        print("HASIL PROXY LIVE (🌐):")
        print("=" * 50)
        csv_list = [item["csv_format"] for item in live_results]
        output_csv = "\n".join(csv_list)
        print(output_csv)
        print("=" * 50)

        print("\nMau simpan hasil proxy LIVE ke file?")
        print("1. Ya")
        print("2. Tidak")
        save_choice = input("Pilih (1/2): ").strip()

        if save_choice == "1" or save_choice.lower() in ["ya", "y"]:
            filename_input = input(
                "Masukkan nama file (tekan Enter untuk default 'live_proxies.txt'): "
            ).strip()
            filename = (
                filename_input
                if filename_input
                else "live_proxies.txt"
            )
            filename = (
                filename
                if filename.endswith(".txt")
                else f"{filename}.txt"
            )

            with open(filename, "w", encoding="utf-8") as f:
                f.write(output_csv)

            print(f"\n✅ Berhasil disimpan ke file: '{filename}'")
        else:
            print("\nℹ️ Hasil tidak disimpan ke file.")


def main():
    print("===================================")
    print("   MULTI-MODE PROXY CHECKER        ")
    print("      • By. K I H E O •            ")
    print("===================================")
    print("1. Mode Paste (Paste Langsung)")
    print("2. Mode File (.txt)")
    print("===================================")

    choice = input("Pilih menu (1/2): ").strip()
    raw_lines = []

    if choice == "1":
        print("\n--- MODE TEMPEL ---")
        print(
            "Tempel daftar IP di bawah ini (ketik 'RUN' atau Enter 2x untuk mulai):\n"
        )
        while True:
            line = input().strip()
            if line.upper() == "RUN" or (line == "" and raw_lines):
                break
            if line:
                raw_lines.append(line)

    elif choice == "2":
        print("\n--- MODE FILE .TXT ---")
        file_path = (
            input("Masukkan nama/path file (misal: proxies.txt): ")
            .strip()
            .strip('"')
            .strip("'")
        )
        if not os.path.exists(file_path):
            print(f"\n❌ File '{file_path}' tidak ditemukan!")
            return
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_lines = f.readlines()
        except Exception as e:
            print(f"❌ Gagal membaca file: {e}")
            return
    else:
        print("\n❌ Pilihan tidak valid.")
        return

    if raw_lines:
        run_checker(raw_lines)


if __name__ == "__main__":
    main()
