import requests
from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

# Your CoinMarketCap API key
API_KEY = 'fa3f6b57-d96a-4b38-8cbe-7255bd48269f'

# Function to fetch cryptocurrency prices using CoinMarketCap API
def get_crypto_prices(cryptos: list) -> str:
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }
    symbols = ','.join([crypto.upper() for crypto in cryptos])
    params = {
        'symbol': symbols,
        'convert': 'USD'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        prices = []
        for crypto in cryptos:
            symbol = crypto.upper()
            if symbol in data['data']:
                price = data['data'][symbol]['quote']['USD']['price']
                prices.append(f"{symbol} - ${price:.2f} USD")
            else:
                prices.append(f"Error fetching the price for {symbol}.")
        return '\n'.join(prices)
    else:
        return "Error fetching the prices. Please try again later."

# Command handler for /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to the Crypto Price Bot! Use /price <crypto1> <crypto2> ... to get the prices of cryptocurrencies.")

# Command handler for /price
async def price(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        # await update.message.reply_text("Please specify at least one cryptocurrency. Usage: /price <crypto1> <crypto2> ...")
        cryptos = ["BTC","AR","GHX","KDA","DOGE"]
    else:
        cryptos = context.args
        
    price_message = get_crypto_prices(cryptos)
    await update.message.reply_text(price_message)

def main() -> None:
    """Start the bot."""
    bot_token = "6142588805:AAHII6-PG3rGxaS4FEjW5YSSb_NtGSDaqYw"
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()