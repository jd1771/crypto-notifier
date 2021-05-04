from coinbase.wallet.client import Client
from coinbase.wallet.error import CoinbaseError
import discord
from discord.ext import tasks
import time
import json
import config

discord_client = discord.Client()
cb_client = Client("fakekey", "fakesecret")


def get_watchlist():
    watchlist_info = "WATCHLIST INFORMATION\n"

    f = open('watchlist.json')
    watchlist = json.load(f)
    watchlist_info += watchlist[0]
    f.close()
    return watchlist_info

def get_pair_data(pair):
    try:
        pair_data = cb_client.get_spot_price(currency_pair = pair)
        return pair_data
    except CoinbaseError as e:
        raise CoinbaseError


def main():
    discord_client = discord.Client()
    cb_client = Client("fakekey", "fakesecret")
    
    @discord_client.event
    async def on_ready():
        print(f'{discord_client.user} has connected to Discord!')
    
    @discord_client.event
    async def on_message(message):
        if message.content.startswith("!price"):
            pair = message.content.split("!price ")[1]
            try:
                pair_data = get_pair_data(pair)
                msg = ("Current Price of %s%s%s is %s" %(pair_data.base,"-",pair_data.currency,str(pair_data.amount)))
                await message.channel.send(msg)
            except CoinbaseError as e:
                await message.channel.send(":exclamation:Error: Invalid/Unsupp[orted pair, type !help for more information")

                
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
        
        elif message.content == "!watchlist":
            pass

        elif message.content == "!help":
            embed_msg = discord.Embed(title="COMMAND INFORMATION", color=0x00ff00)
            embed_msg.add_field(name="!price COIN-CURRENCY", value="Gets the current price of the the coin-currency pair", inline=False)
            embed_msg.add_field(name="!watchlist", value="Get information about the watchlist", inline=False)
            embed_msg.add_field(name="!add COIN-CURRENCY", value="Add coin-currency pair to the watchlist", inline=False)
            embed_msg.add_field(name="!remove COIN-CURRENCY", value="Remove coin-currency pair from the watchlist if it's currently in the watchlist", inline=False)
            await message.channel.send(embed=embed_msg)


        

    
    
    
    
    
    # @tasks.loop(seconds = 10) # repeat after every 10 seconds
    # async def myLoop():
    #     pass
        


    # myLoop.start()

    
    discord_client.run(config.discord_key)

    
if __name__ == "__main__":
    main()
