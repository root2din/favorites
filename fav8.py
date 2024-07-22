import os
import asyncio
import logging
import json
from telethon import TelegramClient
from telegram import Bot
from telegram.constants import ParseMode
from telethon.tl.types import Message, MessageService
from telethon.errors import ChannelPrivateError
from telegram.error import TelegramError

def setup_logging():
    logging.basicConfig(
        filename='telegram_channel_alerts.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def read_value_from_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")

    with open(file_path, 'r') as f:
        return f.readline().strip()

def save_last_message_id(channel, message_id):
    file_path = f"{channel}_last_message_id.json"
    with open(file_path, 'w') as f:
        json.dump(str(message_id), f, ensure_ascii=False, indent=5)

def load_last_message_id(channel):
    file_path = f"{channel}_last_message_id.json"
    if not os.path.exists(file_path):
        return 0

    with open(file_path, 'r') as f:
        content = f.read()

    if not content:
        return 0

    return int(json.loads(content))

def load_channels_from_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")

    with open(file_path, 'r') as f:
        return [line.strip() for line in f.readlines()]

def load_words_from_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")

    with open(file_path, 'r') as f:
        return [line.strip().lower() for line in f.readlines()]

async def read_and_update_keywords(file_path, keywords):
    while True:
        try:
            new_keywords = load_words_from_file(file_path)
            keywords.clear()
            keywords.extend(new_keywords)
            logging.info("Keywords updated")
        except Exception as e:
            logging.error(f"Error updating keywords: {e}")
        await asyncio.sleep(10)  # Чтение каждые 10 секунд

async def read_and_update_channels(file_path, channels):
    while True:
        try:
            new_channels = load_channels_from_file(file_path)
            channels.clear()
            channels.extend(new_channels)
            logging.info("Channels updated")
        except Exception as e:
            logging.error(f"Error updating channels: {e}")
        await asyncio.sleep(15)  # Чтение каждые 15 секунд

async def check_and_send_new_messages():
    setup_logging()

    api_id = read_value_from_file('api_id2.txt')
    api_hash = read_value_from_file('api_hash2.txt')
    token = read_value_from_file('token2.txt')
    chat_id = int(read_value_from_file('chatid3.txt'))

    bot = Bot(token=token)

    async with TelegramClient('session_channel_checker', api_id, api_hash) as client:
        try:
            await client.get_input_entity(chat_id)
        except Exception as e:
            logging.error(f"Cannot find chat with ID {chat_id}: {e}")
            return

        CHANNELS = []
        KEYWORDS = []

        # Стартуем задачи по периодическому чтению файлов с каналами и ключевыми словами
        asyncio.create_task(read_and_update_keywords('words.txt', KEYWORDS))
        asyncio.create_task(read_and_update_channels('channel.txt', CHANNELS))

        while True:
            for channel in CHANNELS:
                last_message_id = load_last_message_id(channel)

                try:
                    last_messages = await client.get_messages(channel, limit=3)
                except ChannelPrivateError as e:
                    logging.error(f"Error getting messages from channel {channel}: {e}")
                    continue
                except TelegramError as e:
                    logging.error(f"General Telegram error for channel {channel}: {e}")
                    continue

                if last_messages:
                    for message in last_messages:
                        if isinstance(message, Message) and not isinstance(message, MessageService):
                            try:
                                if message.id > last_message_id:
                                    text = message.text.lower() if message.text else ""
                                    matched_keywords = [word for word in KEYWORDS if word in text]
                                    if matched_keywords:
                                        keyword_tag = f"#{matched_keywords[0]}"
                                        channel_name = channel.replace('@', '')
                                        link = f"<a href='https://t.me/{channel_name}/{message.id}'>{channel_name}</a>"
                                        new_message_text = f"{keyword_tag} {message.text}\n\nForwarded from {link}"
                                        logging.info(f"Forwarding message ID {message.id} from channel {channel} with keyword {matched_keywords[0]}")
                                        await bot.send_message(chat_id, new_message_text, parse_mode=ParseMode.HTML)
                                        save_last_message_id(channel, message.id)
                            except TelegramError as te:
                                logging.error(f"Error forwarding message ID {message.id} from channel {channel}: {te}")

            await asyncio.sleep(1)

asyncio.run(check_and_send_new_messages())
