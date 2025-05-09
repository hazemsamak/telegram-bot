#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os

import aiohttp
from dotenv import load_dotenv
from telegram import (ForceReply, InlineKeyboardButton, InlineKeyboardMarkup,
                      Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Read API keys from environment variables
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

# Function to search for movies
async def search_movies(query: str) -> list:
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                data = await response.json()
                return data.get('results', [])
    except aiohttp.ClientError as e:
        print(f"Error fetching data from API: {e}")
        return []

# Handler for the /search command
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a movie name to search for.")
        return

    movies = await search_movies(query)
    if not movies:
        await update.message.reply_text("No movies found.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{movie['title']} ({movie['release_date'][:4]})", callback_data=movie['id'])]
        for movie in movies[:10]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Found movies:", reply_markup=reply_markup)

# Handler for the callback query when a user selects a movie
async def movie_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    movie_id = query.data

    # Fetch movie details using the movie_id
    movie_details = await get_movie_details(movie_id)
    if movie_details:
        # Construct the poster URL
        poster_path = movie_details['poster_path']
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None

        # Send movie details with poster
        details_text = (
            f"Title: {movie_details['title']}\n"
            f"Release Date: {movie_details['release_date']}\n"
            f"Overview: {movie_details['overview']}"
        )
        
        if (poster_url):
            await query.message.reply_photo(photo=poster_url, caption=details_text)
        else:
            await query.edit_message_text(text=details_text)
        
        # Ask user for confirmation to add movie to Radarr
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f"add_{movie_id}"), InlineKeyboardButton("No", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Do you want to add this movie to Radarr?", reply_markup=reply_markup)
    else:
        await query.edit_message_text(text="Failed to fetch movie details.")

# Handler for the confirmation callback
async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("add_"):
        movie_id = data.split("_")[1]
        movie_details = await get_movie_details(movie_id)
        if movie_details:
            added_to_radarr = await add_movie_to_radarr(movie_details)
            if added_to_radarr:
                await query.edit_message_text("Movie added to Radarr successfully.")
            else:
                await query.edit_message_text("Failed to add movie to Radarr.")
        else:
            await query.edit_message_text("Failed to fetch movie details.")
    else:
        await query.edit_message_text("Operation cancelled.")

# Function to get movie details by movie_id
async def get_movie_details(movie_id: str) -> dict:
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error fetching movie details from API: {e}")
        return {}

# Function to add movie to Radarr
async def add_movie_to_radarr(movie_details: dict) -> bool:
    radarr_url = "http://sharksbay.ddns.net:7878/api/v3/movie"
    headers = {
        "X-Api-Key": RADARR_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "title": movie_details['title'],
        #"qualityProfileId": 1,  # Adjust based on your Radarr settings
        "titleSlug": movie_details['title'].lower().replace(' ', '-'),
        "tmdbId": movie_details['id'],
        "year": movie_details['release_date'][:4],
        "rootFolderPath": "/external-media/movies",  # Adjust based on your Radarr settings
        "qualityProfileId": 4,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(radarr_url, headers=headers, json=payload) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                return True
    except aiohttp.ClientError as e:
        print(f"Error adding movie to Radarr: {e}")
        return False

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CallbackQueryHandler(movie_selection, pattern=r'^\d+$'))
    application.add_handler(CallbackQueryHandler(confirmation, pattern=r'^add_\d+$|^cancel$'))

    # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()