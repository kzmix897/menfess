from telethon import TelegramClient, events
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ganti dengan informasi yang didapatkan dari Telegram Developer
api_id = '29050819'
api_hash = 'e801321d49ec12a06f52a91ee3ff284e'
bot_token = '7546042741:AAGii1xQR_mA4AiReH0GykSpgKJx7he1D98'

# Session untuk akun kedua yang akan mengirim pesan
session_file = 'akun_kedua.session'
phone_number_akun_kedua = '+62 856 92226889'

# Buat client untuk bot dan akun kedua
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
akun_kedua = TelegramClient(session_file, api_id, api_hash)

# Dictionary untuk menyimpan pengirim anonim dan target
message_mapping = {}

# Fungsi untuk menjelaskan cara kerja bot
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await bot.send_message(
        event.sender_id, 
        "Selamat datang di bot Menfess anonim!\n\n"
        "Cara kerja bot ini:\n"
        "1. Gunakan perintah /menfess @username pesanmu untuk mengirim pesan anonim ke pengguna lain.\n"
        "2. Pengguna akan menerima pesan dengan ID yang bisa digunakan untuk membalas.\n"
        "3. Pengguna yang menerima pesan dapat membalas menggunakan perintah /reply <id pesan> <pesan>.\n"
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
            # Kirim pesan ke pengguna B
            sent_message = await akun_kedua.send_message(
                target_username, 
                f"Anda menerima pesan anonim: {message_content}\n"
                "ID pesan: {id}\n"  # Placeholder untuk ID pesan
                "Balas menggunakan bot @Forceesubs_bot dengan menggunakan perintah: /reply <id pesan> <pesan>"
            )

            # Simpan ID pesan yang dikirim dan pengirim asli
            message_mapping[sent_message.id] = {
                'pengirim_asli': event.sender_id,
                'target_username': target_username
            }

            # Mengupdate pesan untuk menyertakan ID pesan yang sebenarnya
            await sent_message.edit(
                f"Anda menerima pesan anonim: {message_content}\n"
                f"ID pesan: `{sent_message.id}`\n"
                "Balas menggunakan bot @Forceesubs_bot dengan menggunakan perintah: /reply <id pesan> <pesan>"
            )

            # Kirim instruksi ke pengguna A
            await bot.send_message(
                event.sender_id,  # Kirim instruksi ke Pengguna A
                f"Pesan berhasil dikirim ke {target_username}.\n"
                f"ID pesan: {sent_message.id}\n"  # Menggunakan format monospace
                f"Silakan gunakan bot ini untuk membalas: /reply {sent_message.id} <pesan>"
            )

            await event.reply(f"Pesan dikirim ke {target_username} dengan ID: {sent_message.id}.")  # Menggunakan format monospace
            logger.info(f"Pesan ke {target_username} berhasil dikirim. ID pesan: {sent_message.id}")
        except Exception as e:
            await event.reply(f"Gagal mengirim pesan: {str(e)}")
            logger.error(f"Gagal mengirim pesan: {str(e)}")

# Fungsi untuk menangani perintah /reply dari Pengguna B
@bot.on(events.NewMessage(pattern='/reply'))
async def reply_handler(event):
    logger.info("Memeriksa perintah reply...")
    command_parts = event.message.text.split(maxsplit=2)
    if len(command_parts) < 3:
        await event.reply("Format salah. Gunakan: /reply <id pesan> <balasanmu>")
        return

    try:
        reply_id = int(command_parts[1])
    except ValueError:
        await event.reply("ID pesan harus berupa angka.")
        return

    reply_content = command_parts[2]
    # Cek apakah ID pesan ada di message_mapping
    if reply_id in message_mapping:
        pengirim_asli = message_mapping[reply_id]['pengirim_asli']
        target_username = message_mapping[reply_id]['target_username']

        logger.info(f"Mengirim balasan ke {pengirim_asli} dengan konten: {reply_content}")
        await bot.send_message(
            pengirim_asli, 
            f"Balasan dari {target_username}:\n{reply_content}"
        )

        await event.reply("Balasan dikirim ke pengirim asli.")
        logger.info(f"Balasan dikirim ke {pengirim_asli}. Konten: {reply_content}")
    else:
        await event.reply("ID pesan tidak valid atau tidak ditemukan.")
        logger.warning("ID pesan tidak ditemukan untuk dibalas.")

# Fungsi untuk login akun kedua jika belum login
async def login_akun_kedua():
    async with akun_kedua:
        if not await akun_kedua.is_user_authorized():
            await akun_kedua.send_code_request(phone_number_akun_kedua)
            code = input("Masukkan kode otentikasi yang dikirimkan ke akun kedua: ")
            await akun_kedua.sign_in(phone_number_akun_kedua, code)

# Jalankan login akun kedua dan bot
akun_kedua.start()
akun_kedua.loop.run_until_complete(login_akun_kedua())
bot.run_until_disconnected()
