from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait
from pyrogram.file_id import FileId
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from helper.utils import progress_for_pyrogram, convert, humanbytes, add_prefix_suffix, remove_path
from helper.database import digital_botz
from helper.ffmpeg import change_metadata
from config import Config
from asyncio import sleep
import os, time, asyncio

UPLOAD_TEXT = "Uploading Started...."
DOWNLOAD_TEXT = "Download Started..."

app = Client("4gb_FileRenameBot", api_id=Config.API_ID, api_hash=Config.API_HASH, session_string=Config.STRING_SESSION)

@Client.on_message(filters.private & (filters.audio | filters.document | filters.video))
async def rename_start(client, message):
    user_id  = message.from_user.id
    rkn_file = getattr(message, message.media.value)
    filename = rkn_file.file_name
    filesize = humanbytes(rkn_file.file_size)
    mime_type = rkn_file.mime_type
    dcid = FileId.decode(rkn_file.file_id).dc_id
    extension_type = mime_type.split('/')[0]

    # --- Daily Limit සහ Premium check එක සම්පූර්ණයෙන්ම ඉවත් කළා ---
    try:
        await message.reply_text(
            text=f"**__ᴍᴇᴅɪᴀ ɪɴꜰᴏ:\n\n◈ ᴏʟᴅ ꜰɪʟᴇ ɴᴀᴍᴇ: `{filename}`\n\n◈ ᴇxᴛᴇɴꜱɪᴏɴ: `{extension_type.upper()}`\n◈ ꜰɪʟᴇ ꜱɪᴢᴇ: `{filesize}`\n◈ ᴍɪᴍᴇ ᴛʏᴇᴩ: `{mime_type}`\n◈ ᴅᴄ ɪᴅ: `{dcid}`\n\nᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇɴᴀᴍᴇ ᴡɪᴛʜ ᴇxᴛᴇɴsɪᴏɴ ᴀɴᴅ ʀᴇᴘʟʏ ᴛʜɪs ᴍᴇssᴀɢᴇ....__**",
            reply_to_message_id=message.id,  
            reply_markup=ForceReply(True)
        )       
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await rename_start(client, message)

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
            if "." in media.file_name:
                extn = media.file_name.rsplit('.', 1)[-1]
            else:
                extn = "mkv"
            new_name = new_name + "." + extn
        await reply_message.delete()

        # මෙතන කෙලින්ම Document button එක විතරක් තැබුවා Thumbnail කරදරය නැති කිරීමට
        button = [[InlineKeyboardButton("📁 Dᴏᴄᴜᴍᴇɴᴛ (Nᴏ Tʜᴜᴍʙ)", callback_data = "upload#document")]]
        await message.reply(
            text=f"**Sᴇʟᴇᴄᴛ Tʜᴇ Oᴜᴛᴩᴜᴛ Fɪʟᴇ Tyᴩᴇ**\n**• Fɪʟᴇ Nᴀᴍᴇ :-**`{new_name}`",
            reply_to_message_id=file.id,
            reply_markup=InlineKeyboardMarkup(button)
        )

async def upload_files(bot, sender_id, upload_type, file_path, ph_path, caption, duration, rkn_processing):
    try:
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
        
        # 'thumb=None' ලෙස වෙනස් කළා, එවිට කිසිම Thumbnail එකක් යන්නේ නැත
        filw = await bot.send_document(
            sender_id,
            document=file_path,
            thumb=None, 
            caption=caption,
            progress=progress_for_pyrogram,
            progress_args=(UPLOAD_TEXT, rkn_processing, time.time()))
        return filw, None
    except Exception as e:
        return None, str(e)

@Client.on_callback_query(filters.regex("upload"))
async def upload_doc(bot, update):
    rkn_processing = await update.message.edit("`Processing...`")
    user_id = int(update.message.chat.id) 
    new_name = update.message.text
    new_filename_ = new_name.split(":-")[1]
    user_data = await digital_botz.get_user_data(user_id)

    prefix = user_data.get('prefix', None)
    suffix = user_data.get('suffix', None)
    new_filename = await add_prefix_suffix(new_filename_, prefix, suffix)

    file = update.message.reply_to_message
    media = getattr(file, file.media.value)
    file_path = f"Renames/{new_filename}"

    await rkn_processing.edit("`Downloading Started...`")
    try:            
        dl_path = await bot.download_media(message=file, file_name=file_path, progress=progress_for_pyrogram, progress_args=(DOWNLOAD_TEXT, rkn_processing, time.time()))                    
    except Exception as e:
        return await rkn_processing.edit(f"Download Error: {e}")

    await rkn_processing.edit("`Uploading Started...`")
    
    caption = f"**{new_filename}**"
    upload_type = "document" # Force as document

    # 4GB+ හෝ 2GB check එක පිරිසිදු කළා
    filw, error = await upload_files(bot, update.message.chat.id, upload_type, dl_path, None, caption, 0, rkn_processing)
                   
    if error:
        await remove_path(None, file_path, dl_path, None)
        return await rkn_processing.edit(f"Upload Error: {error}")        

    await remove_path(None, file_path, dl_path, None)
    return await rkn_processing.edit("Uploaded Successfully....")
