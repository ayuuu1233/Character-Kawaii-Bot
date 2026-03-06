from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import db, collection, user_collection
from shivu import shivuu as app
from shivu import SPECIALGRADE, GRADE1
import asyncio
import random
import time

backup_collection = db["backup_collection"]

async def backup_characters(user_id):
    user = await user_collection.find_one({'id': user_id})
    if user:
        await backup_collection.insert_one({'user_id': user_id, 'characters': user['characters'], 'timestamp': time.time()})

async def restore_characters(user_id, timestamp):
    backup = await backup_collection.find_one({'user_id': user_id, 'timestamp': {'$lte': timestamp}}, sort=[('timestamp', -1)])
    if backup:
        await user_collection.update_one({'id': user_id}, {'$set': {'characters': backup['characters']}})
        return True
    return False

async def update_user_rank(user_id):
    # Implementation for updating user rank
    pass

async def send_action_notification(message: str):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Reverse", callback_data=f"reverse_{time.time()}")]
    ])
    for user_id in SPECIALGRADE:
        try:
            await app.send_message(user_id, message, reply_markup=keyboard)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

async def give_character_batch(receiver_id, character_ids):
    characters = await collection.find({'id': {'$in': character_ids}}).to_list(length=len(character_ids))
    if characters:
        try:
            await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': {'$each': characters}}})
            await update_user_rank(receiver_id)
            return characters
        except Exception as e:
            print(f"Error updating user: {e}")
            raise
    else:
        raise ValueError("Some characters not found.")

@app.on_message(filters.command(["daan"]) & filters.reply)
async def give_character_command(client, message):
    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        await message.reply_text("This command can only be used by Special Grade and Grade 1 sorcerers.")
        return

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to give a character!")
        return

    try:
        character_ids = message.text.split()[1:]
        if not character_ids:
            await message.reply_text("Please provide at least one character ID.")
            return

        receiver_id = message.reply_to_message.from_user.id
        receiver_first_name = message.reply_to_message.from_user.first_name
        sender_first_name = message.from_user.first_name

        # Ensure the bot has interacted with the receiver
        try:
            await client.get_chat(receiver_id)
        except Exception as e:
            await message.reply_text(f"Error interacting with the receiver: {e}")
            return

        # Backup user characters before giving
        await backup_characters(receiver_id)

        # Give characters to the receiver
        characters = await give_character_batch(receiver_id, character_ids)

        if characters:
            character_list = "\n".join(
                [f"ID: {char['id']}, Name: {char['name']}, Rarity: {char['rarity']}" for char in characters]
            )
            img_url = characters[0]['img_url']  # Use the first character's image for the reply
            user_link = f"[{receiver_first_name}](tg://user?id={receiver_id})"

            caption = (
                f"🎉 {user_link}, you have received {len(characters)} character(s) from {sender_first_name}!\n\n"
                f"📜 Details of given characters:\n{character_list}"
            )
            await message.reply_photo(photo=img_url, caption=caption)

            # Send notification to SPECIALGRADE users
            notification_message = (
                f"Action: Give Character\n"
                f"Given by: {sender_first_name}\n"
                f"Receiver: {user_link}\n"
                f"Character IDs: {', '.join(character_ids)}"
            )
            await send_action_notification(notification_message)
    except Exception as e:
        print(f"Error in give_character_command: {e}")
        await message.reply_text("An error occurred while processing the command.")

@app.on_message(filters.command(["kill"]) & filters.reply)
async def remove_character_command(client, message):
    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        await message.reply_text("This command can only be used by Special Grade and Grade 1 sorcerers.")
        return

    if not message.reply_to_message:
        await message.reply_text("You need to reply to a user's message to remove a character!")
        return

    try:
        character_ids = message.text.split()[1:]
        if not character_ids:
            await message.reply_text("Please provide at least one character ID to remove.")
            return

        receiver_id = message.reply_to_message.from_user.id
        receiver_first_name = message.reply_to_message.from_user.first_name
        sender_first_name = message.from_user.first_name

        # Ensure the bot has interacted with the receiver
        try:
            await client.get_chat(receiver_id)
        except Exception as e:
            await message.reply_text(f"Error interacting with the receiver: {e}")
            return

        # Backup user characters before removing
        await backup_characters(receiver_id)

        removed_characters = []
        for character_id in character_ids:
            character = await collection.find_one({'id': character_id})
            if character:
                await user_collection.update_one({'id': receiver_id}, {'$pull': {'characters': {'id': character_id}}})
                removed_characters.append(character)

        if removed_characters:
            character_list = "\n".join(
                [f"ID: {char['id']}, Name: {char['name']}, Rarity: {char['rarity']}" for char in removed_characters]
            )
            user_link = f"[{receiver_first_name}](tg://user?id={receiver_id})"

            await message.reply_text(
                f"🚫 {len(removed_characters)} character(s) have been removed from {user_link}'s collection:\n\n"
                f"{character_list}"
            )

            # Send notification to SPECIALGRADE users
            notification_message = (
                f"Action: Remove Character\n"
                f"Removed by: {sender_first_name}\n"
                f"Receiver: {user_link}\n"
                f"Character IDs: {', '.join(character_ids)}"
            )
            await send_action_notification(notification_message)
        else:
            await message.reply_text("No characters found for the given IDs.")
    except Exception as e:
        print(f"Error in remove_character_command: {e}")
        await message.reply_text("An error occurred while processing the command.")

@app.on_message(filters.command(["given"]))
async def random_characters_command(client, message):
    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        await message.reply_text("This command can only be used by Special Grade and Grade 1 sorcerers.")
        return

    try:
        if not message.reply_to_message:
            await message.reply_text("You need to reply to a user's message to give characters!")
            return

        if len(message.command) < 2:
            await message.reply_text("Please provide the amount of random characters to give.")
            return

        try:
            amount = int(message.command[1])
        except ValueError:
            await message.reply_text("Invalid amount. Please provide a valid number.")
            return

        amount = min(amount, 2000)

        receiver_id = message.reply_to_message.from_user.id

        # Ensure the bot has interacted with the receiver
        try:
            await client.get_chat(receiver_id)
        except Exception as e:
            await message.reply_text(f"Error interacting with the receiver: {e}")
            return

        # Backup user characters before giving
        await backup_characters(receiver_id)

        all_characters_cursor = collection.find({})
        all_characters = await all_characters_cursor.to_list(length=None)

        # Check for 'id' field presence
        all_characters = [character for character in all_characters if 'id' in character]

        if len(all_characters) < amount:
            await message.reply_text("Not enough characters available to give.")
            return

        random_characters = random.sample(all_characters, amount)
        random_character_ids = [character['id'] for character in random_characters]

        # Process tasks in batches to optimize performance
        batch_size = 100  # Adjust batch size as needed
        tasks = [
            give_character_batch(receiver_id, random_character_ids[i:i + batch_size])
            for i in range(0, amount, batch_size)
        ]

        await asyncio.gather(*tasks)

        giver_name = message.from_user.first_name
        user_link = f"[{message.reply_to_message.from_user.first_name}](tg://user?id={receiver_id})"

        # Send a message to the receiver, mentioning the giver and the amount of characters given
        await message.reply_to_message.reply_text(
            f"{giver_name} has given you {amount} character(s)!"
        )

        # Send summary notification to the owner
        notification_message = (
            f"Action: Give Random Characters\n"
            f"Given by: {giver_name}\n"
            f"Amount: {amount}\n"
            f"Receiver: {user_link}\n"
        )
        await send_action_notification(notification_message)
    except Exception as e:
        print(f"Error in random_characters_command: {e}")
        await message.reply_text("An error occurred while processing the command.")

@app.on_callback_query(filters.regex(r'^reverse_\d+\.\d+$'))
async def reverse_action(client, callback_query: CallbackQuery):
    timestamp = float(callback_query.data.split("_")[1])
    target_id = callback_query.message.chat.id

    if str(callback_query.from_user.id) in SPECIALGRADE:
        restored = await restore_characters(target_id, timestamp)
        if restored:
            await callback_query.edit_message_text("The action has been reversed.")
        else:
            await callback_query.answer("Failed to reverse the action or no backup found.", show_alert=True)
    else:
        await callback_query.answer("You don't have permission to reverse actions.", show_alert=True)
