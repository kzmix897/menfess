import logging
import random
import string
from telethon import TelegramClient, events
import socket
import asyncio

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Logger untuk bot
bot_logger = logging.getLogger('bot_logger')
bot_logger.setLevel(logging.INFO)

# Logger untuk health check, disimpan ke file terpisah
health_logger = logging.getLogger('health_logger')
health_logger.setLevel(logging.INFO)
health_handler = logging.FileHandler('health_check.log')
health_logger.addHandler(health_handler)

# Ganti dengan informasi yang didapatkan dari Telegram Developer
API_ID = '29050819'
API_HASH = 'e801321d49ec12a06f52a91ee3ff284e'
BOT_TOKEN = '7109883302:AAE_pS7K-XE6h2SRqlgiSH4wrRi5Q2hjyC8'

# Session untuk akun kedua yang akan mengirim pesan
session_file = 'akun_kedua.session'
phone_number_akun_kedua = '+62 856 92226889'

# Buat client untuk bot dan akun kedua
bot = TelegramClient('bot', API_ID, API_HASH).start(BOT_TOKEN=BOT_TOKEN)
akun_kedua = TelegramClient(session_file, API_ID, API_HASH)

# Dictionary untuk menyimpan pengirim anonim dan target
message_mapping = {}

# Fungsi untuk menghasilkan kode rahasia unik
def generate_token(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Fungsi untuk menjelaskan cara kerja bot
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    bot_logger.info(f"Perintah /start diterima dari {event.sender_id}")
    await bot.send_message(
        event.sender_id, 
        "Selamat datang di bot Menfess anonim!\n\n"
        "Cara kerja bot ini:\n"
        "1. Gunakan perintah /menfess @username pesanmu untuk mengirim pesan anonim ke pengguna lain.\n"
        "2. Pengguna akan menerima pesan dengan kode rahasia untuk membalas.\n"
        "3. Pengguna yang menerima pesan dapat membalas menggunakan perintah /reply <kode rahasia> <pesan>.\n"
        "4. Semua pesan bersifat anonim, baik pengirim maupun penerima tidak mengetahui identitas satu sama lain."
    )
    logger.info(f"User {event.sender_id} memulai bot dengan perintah /start")

# Fungsi untuk mengirim panduan ke user baru
@bot.on(events.ChatAction)
async def handler(event):
    if event.user_added or event.user_joined:
        user = await event.get_user()
        await bot.send_message(user.id, 
                               "Selamat datang! Untuk mengirim pesan menfess, gunakan format:\n"
                               "/menfess @username pesanmu")

# Fungsi untuk menangani perintah /menfess
@bot.on(events.NewMessage(pattern='/menfess'))
async def menfess_handler(event):
    command_parts = event.message.text.split(maxsplit=2)
    if len(command_parts) < 3:
        await event.reply("Format salah. Gunakan: /menfess @username pesanmu")
        return
    
    target_username = command_parts[1]
    message_content = command_parts[2]

    async with akun_kedua:
        try:
            # Generate kode rahasia
            token = generate_token()
            
            # Kirim pesan ke pengguna B
            sent_message = await akun_kedua.send_message(
                target_username, 
                f"Anda menerima pesan anonim: {message_content}\n"
                f"Kode rahasia: `{token}`\n"  # Kode rahasia yang dihasilkan
                "Balas menggunakan bot @menfess_fasbot dengan menggunakan perintah: /reply <kode rahasia> <pesan>"
            )

            # Simpan token yang dikirim dan pengirim asli
            message_mapping[token] = {
                'pengirim_asli': event.sender_id,
                'target_username': target_username,
                'message_id': sent_message.id
            }

            # Kirim instruksi ke pengguna A
            await bot.send_message(
                event.sender_id,  # Kirim instruksi ke Pengguna A
                f"Pesan berhasil dikirim ke {target_username}.\n"
                f"Kode rahasia: `{token}`\n"  # Menggunakan format monospace
                f"Silakan gunakan bot ini untuk membalas: /reply {token} <pesan>"
            )

            await event.reply(f"Pesan dikirim ke {target_username} dengan Kode rahasia: `{token}`.")  # Menggunakan format monospace
            bot_logger.info(f"Pesan ke {target_username} berhasil dikirim. Kode rahasia: {token}")
        except Exception as e:
            await event.reply(f"Gagal mengirim pesan: {str(e)}")
            bot_logger.error(f"Gagal mengirim pesan: {str(e)}")

# Fungsi untuk menangani perintah /reply dari Pengguna B
@bot.on(events.NewMessage(pattern='/reply'))
async def reply_handler(event):
    bot_logger.info("Memeriksa perintah reply...")
    command_parts = event.message.text.split(maxsplit=2)
    if len(command_parts) < 3:
        await event.reply("Format salah. Gunakan: /reply <kode rahasia> <balasanmu>")
        return

    token = command_parts[1]
    reply_content = command_parts[2]
    
    # Cek apakah kode rahasia ada di message_mapping
    if token in message_mapping:
        pengirim_asli = message_mapping[token]['pengirim_asli']
        target_username = message_mapping[token]['target_username']

        bot_logger.info(f"Mengirim balasan ke {pengirim_asli} dengan konten: {reply_content}")
        await bot.send_message(
            pengirim_asli, 
            f"Balasan dari {target_username}:\n{reply_content}"
        )

        await event.reply("Balasan dikirim ke pengirim asli.")
        bot_logger.info(f"Balasan dikirim ke {pengirim_asli}. Konten: {reply_content}")
    else:
        await event.reply("Kode rahasia tidak valid atau tidak ditemukan.")
        bot_logger.warning("Kode rahasia tidak ditemukan untuk dibalas.")

# Fungsi untuk login akun kedua jika belum login
async def login_akun_kedua():
    async with akun_kedua:
        if not await akun_kedua.is_user_authorized():
            await akun_kedua.send_code_request(phone_number_akun_kedua)
            code = input("Masukkan kode otentikasi yang dikirimkan ke akun kedua: ")
            await akun_kedua.sign_in(phone_number_akun_kedua, code)

# Fungsi Health Check TCP di port 8000
async def tcp_health_check():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 8000))
    server.listen(5)
    health_logger.info("Health check server berjalan di port 8000")

    while True:
        client_socket, client_address = server.accept()
        # Tambah log hanya untuk debugging jika dibutuhkan
        health_logger.info(f"Terhubung dengan {client_address}")
        client_socket.close()

# Jalankan health check secara asynchronous
async def main():
    await asyncio.gather(
        login_akun_kedua(),  # Login akun kedua
        tcp_health_check()   # Mulai health check di port 8000
    )

# Mulai bot dan jalankan health check
akun_kedua.start()
akun_kedua.loop.run_until_complete(main())
bot.run_until_disconnected()
