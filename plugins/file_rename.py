from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
import os, time, asyncio, shutil
from helper.utils import progress_for_pyrogram, humanbytes

UPLOAD_TEXT = "Uploading Started...."
DOWNLOAD_TEXT = "Download Started..."

@Client.on_message(filters.private & (filters.audio | filters.document | filters.video))
async def rename_start(client, message):
    rkn_file = getattr(message, message.media.value)
    filename = rkn_file.file_name
    filesize = humanbytes(rkn_file.file_size)
    
    try:
        await message.reply_text(
            text=f"**__ᴍᴇᴅɪᴀ ɪɴꜰᴏ:\n\n◈ ꜰɪʟᴇ ɴᴀᴍᴇ: `{filename}`\n◈ ꜰɪʟᴇ ꜱɪᴢᴇ: `{filesize}`\n\nᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ....__**",
            reply_to_message_id=message.id,  
            reply_markup=ForceReply(True)
        )       
    except FloodWait as e:
        await asyncio.sleep(e.value)

@Client.on_message(filters.private & filters.reply)
async def refunc(client, message):
    reply_message = message.reply_to_message
    if (reply_message.reply_markup) and isinstance(reply_message.reply_markup, ForceReply):
        new_name = message.text 
        await message.delete() 
        msg = await client.get_messages(message.chat.id, reply_message.id)
        file = msg.reply_to_message
        media = getattr(file, file.media.value)
        
        if not "." in new_name:
            extn = media.file_name.rsplit('.', 1)[-1] if "." in media.file_name else "mkv"
            new_name = new_name + "." + extn
            
        await reply_message.delete()
        
        button = [[InlineKeyboardButton("📁 Uᴘʟᴏᴀᴅ As Dᴏᴄᴜᴍᴇɴᴛ", callback_data = "upload#document")]]
        await message.reply(
            text=f"**Fɪʟᴇ Nᴀᴍᴇ :-** `{new_name}`",
            reply_to_message_id=file.id,
            reply_markup=InlineKeyboardMarkup(button)
        )

@Client.on_callback_query(filters.regex("upload"))
async def upload_doc(bot, update):
    # ඉඩ ඉතිරි කරගන්න පරණ renames ෆෝල්ඩර් එක සම්පූර්ණයෙන්ම ක්ලීන් කරමු
    if os.path.isdir("/tmp/renames"):
        shutil.rmtree("/tmp/renames")
    os.makedirs("/tmp/renames")

    rkn_processing = await update.message.edit("`Processing...`")
    new_name_raw = update.message.text
    new_filename = new_name_raw.split(":-")[1].strip() if ":-" in new_name_raw else "renamed_file"

    file = update.message.reply_to_message
    media = getattr(file, file.media.value)
    dl_path = f"/tmp/renames/{new_filename}"

    await rkn_processing.edit("`Downloading...`")
    try:            
        file_path = await bot.download_media(message=file, file_name=dl_path, progress=progress_for_pyrogram, progress_args=(DOWNLOAD_TEXT, rkn_processing, time.time()))                    
    except Exception as e:
        return await rkn_processing.edit(f"Download Error: {e}")

    await rkn_processing.edit("`Uploading...`")
    try:
        await bot.send_document(
            update.message.chat.id,
            document=file_path,
            thumb=None,
            caption=f"**{new_filename}**",
            progress=progress_for_pyrogram,
            progress_args=(UPLOAD_TEXT, rkn_processing, time.time())
        )
        await rkn_processing.edit("Uploaded Successfully!")
    except Exception as e:
        await rkn_processing.edit(f"Upload Error: {e}")
    finally:
        # වැදගත්ම කොටස: ෆයිල් එක අප්ලෝඩ් වුණත් නැතත් සර්වර් එකෙන් මකා දමන්න
        if os.path.exists(dl_path):
            os.remove(dl_path)
        # මුළු ෆෝල්ඩර් එකම ක්ලීන් කරන්න
        shutil.rmtree("/tmp/renames", ignore_errors=True)
