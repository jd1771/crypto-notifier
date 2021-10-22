import threading
import discord
import asyncio
from datetime import datetime
from coinbase.wallet.client import Client
from coinbase.wallet.error import CoinbaseError
from pymongo import MongoClient
from bson.objectid import ObjectId
import config

cluster = MongoClient(config.db_key)
database = cluster["discord"]
collection = database["alerts"]
_loop = asyncio.get_event_loop()
discord_client = discord.Client()
cb_client = Client("fakekey", "fakesecret")


#   Attempt to get the user requested pair data through the Coinbase API
#   str -> price_info
def get_pair_data(pair):
    try:
        pair_data = cb_client.get_spot_price(currency_pair = pair)
        return pair_data
    except CoinbaseError as e:
        raise CoinbaseError


#   Insert alert data to the database
#   dict -> int (data insert id)
def insert(dict):
    inserted_document = collection.insert_one(dict)
    data_id = inserted_document.inserted_id
    document = collection.find({"_id": ObjectId(data_id)})


#   Scan the alert_list and notify user if their target price has been reached
#   none -> none
def scan_alerts():
    while(True):
        alert_list = collection.find({})
        for alert in alert_list:
            alert_id = alert["_id"]
            ticker = alert['ticker']
            date = alert['date']
            target_price = float(alert['price'])
            direction = alert['direction']
            cur_pair_data = get_pair_data(ticker)
            if (direction == 'below'):
                if (float(cur_pair_data.amount) <= target_price):
                    collection.delete_one({"_id": ObjectId(alert_id)})
                    elapsed_time = datetime.now() - date
                    asyncio.run_coroutine_threadsafe(send_message(alert,elapsed_time), _loop)
            else:
                if (float(cur_pair_data.amount) >= target_price):
                    collection.delete_one({"_id": ObjectId(alert_id)})
                    elapsed_time = datetime.now() - date 
                    asyncio.run_coroutine_threadsafe(send_message(alert,elapsed_time), _loop)


#   Send private message to user given alert
#   dict, int -> none
@discord_client.event
async def send_message(alert,elapsed_time):
    user = await discord_client.fetch_user(alert["user_id"])
    total_seconds = elapsed_time.total_seconds()
    days = divmod(total_seconds,86400)
    hours = divmod(total_seconds,3600)
    mins = divmod(total_seconds,60)
    output_string = "Your target point of {} for {} has been reached in {} days {} hours {} minutes {:.1f} seconds :white_check_mark:".format(alert["price"], alert["ticker"], days[0], hours[0], mins[0], mins[1])
    await user.send(output_string)
   

#   Asyc event to confirm successful bot login
#   none -> none
@discord_client.event
async def on_ready():
    print(f'{discord_client.user} has connected to Discord!')
    
    x = threading.Thread(target=scan_alerts, args=())
    x.start()
    
    
#   Asyc event that handles user input from the discord server
#   message ->  none
@discord_client.event
async def on_message(message):
    if message.content.startswith("!price"):
        pair = message.content.split("!price ")[1]
        try:
            pair_data = get_pair_data(pair)
            msg = ("Current Price of {}-{} is {}".format(pair_data.base, pair_data.currency, str(pair_data.amount)))
            await message.channel.send(msg)
        except CoinbaseError as e:
            await message.channel.send(":exclamation:Error: Invalid/Unsupported pair, type !help for more information")
    
    elif message.content.startswith("!notify"):
        
        user_input_str = message.content.strip("!notify ")
        user_input = user_input_str.split(" ")
        
        if len(user_input) < 2:
            await message.channel.send(":exclamation:Error: Invalid command, type !help for more information")
        try:
            pair_data = get_pair_data(user_input[0])
        except CoinbaseError as e:
            await message.channel.send(":exclamation:Error: Invalid/Unsupported pair, type !help for more information")
            return
        try:
            input_price = float(user_input[1])
        except ValueError as e:
            await message.channel.send(":exclamation:Error: Invalid target price point")
            return
            
        cur_price = float(pair_data.amount)
        
        if cur_price >= input_price:
            alert = {"user_id": message.author.id, "ticker": user_input[0].upper(), "price": input_price, "direction": "below", "date": datetime.now()}
            insert(alert)
        else:
            alert = {"user_id": message.author.id, "ticker": user_input[0].upper(), "price": input_price, "direction": "above", "date": datetime.now()}
            insert(alert)
            
    elif message.content == "!help":
        date = datetime.now()
        embed_msg = discord.Embed(title="COMMAND INFORMATION", color=0x00ff00)
        embed_msg.add_field(name="!price COIN-CURRENCY", value="Gets the current price of the coin-currency pair", inline=False)
        embed_msg.add_field(name="!remove COIN-CURRENCY", value="Remove coin-currency pair from the watchlist if it's currently in the watchlist", inline=False)
        embed_msg.add_field(name="!notify COIN-CURRENCY PRICE", value="Send notification to user when specified price of the given coin is reached", inline=False)
        await message.channel.send(embed=embed_msg)

  
discord_client.run(config.discord_key)





    
