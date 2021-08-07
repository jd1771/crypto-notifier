import threading
import discord
import asyncio
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


#   Get watchlist information
#   none -> str    
def get_watchlist():
    watchlist_info = "WATCHLIST INFORMATION\n\n"
    f = open('watchlist.json')
    watchlist = json.load(f)
    watchlist_info += watchlist[0]
    f.close()
    return watchlist_info

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
        #bprint("dsgfdg")
        alert_list = collection.find({})
        for alert in alert_list:
            alert_id = alert["_id"]
            ticker = alert['ticker']
            target_price = float(alert['price'])
            direction = alert['direction']
            cur_pair_data = get_pair_data(ticker)
            if (direction == 'below'):
                if (float(cur_pair_data.amount) <= target_price):
                    collection.delete_one({"_id": ObjectId(alert_id)})
                    
                    asyncio.run_coroutine_threadsafe(send_message(alert), _loop)
            else:
                if (float(cur_pair_data.amount) >= target_price):
                    collection.delete_one({"_id": ObjectId(alert_id)})
                        
                    asyncio.run_coroutine_threadsafe(send_message(alert), _loop)





#   Send private message to user given alert
#   dict, int -> none
@discord_client.event
async def send_message(alert):
    user = await discord_client.fetch_user(alert["user_id"])
    output_string = "Your target point of {} has been reached for {}".format(alert["price"],alert["ticker"])
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

            
    elif message.content.startswith("!add"):
        try:
            pair = message.content.split("!add ")[1]
            pair_data = get_pair_data(pair)
            pair = pair_data.base + "-" + pair_data.currency
            with open("watchlist.json", "r+") as f:
                data = json.load(f)
                if pair in data:
                    await message.channel.send("Coin already in watchlist!")
                else:
                    data.append(pair)
                    f.seek(0)
                    json.dump(data,f)
                    f.truncate()
                    await message.channel.send("Coin successfully added to watchlist!")
            f.close()
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
            alert = {"user_id": message.author.id, "ticker": user_input[0].upper(), "price": input_price, "direction": "below"}
            insert(alert)
            
        else:
            alert = {"user_id": message.author.id, "ticker": user_input[0].upper(), "price": input_price, "direction": "above"}
            insert(alert)
            
    elif message.content == "!help":
        embed_msg = discord.Embed(title="COMMAND INFORMATION", color=0x00ff00)
        embed_msg.add_field(name="!price COIN-CURRENCY", value="Gets the current price of the coin-currency pair", inline=False)
        embed_msg.add_field(name="!watchlist", value="Get information about the watchlist", inline=False)
        embed_msg.add_field(name="!add COIN-CURRENCY", value="Add coin-currency pair to the watchlist", inline=False)
        embed_msg.add_field(name="!remove COIN-CURRENCY", value="Remove coin-currency pair from the watchlist if it's currently in the watchlist", inline=False)
        embed_msg.add_field(name="!notify COIN-CURRENCY PRICE", value="Send notification to user when specified price of the given coin is reached", inline=False)
        await message.channel.send(embed=embed_msg)

    elif message.content == "!watchlist":
        watchlist_info = get_watchlist()
        embedVar = discord.Embed(title="Watchlist Information", color=0x00ff00)
        embedVar.add_field(name="Field1", value="hi", inline=False)
        embedVar.add_field(name="Field2", value="hi2", inline=False)
        await message.channel.send(embed=embedVar)

discord_client.run(config.discord_key)





    
