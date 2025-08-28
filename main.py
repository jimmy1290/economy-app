import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import random
import datetime

admin_name = "admin"  # Replace with the ROLE NAME for admins

# -----------------------------
# Bot Setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# Data Storage
# -----------------------------
if not os.path.exists("countries.json"):
    with open("countries.json", "w") as f:
        json.dump({}, f)

def load_data():
    with open("countries.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("countries.json", "w") as f:
        json.dump(data, f, indent=4)

# -----------------------------
# Shop Items (UNCHANGED)
# -----------------------------
shop_items = {
    "farm": {"price": 500, "income": 50},
    "coal factory": {"price": 1500, "income": 150},
    "iron factory": {"price": 3000, "income": 300},
    "clothes factory": {"price": 5000, "income": 750},
    "food factory": {"price": 25000, "income": 5000},
    "diamond factory": {"price": 65000, "income": 16500},
    "store": {"price": 250, "income": 500},
    "bank": {"price": 10000, "income": 2000},
    "mine": {"price": 5000, "income": 1000},
    "oil_rig": {"price": 20000, "income": 4000},
    "tourism1": {"price": 8000, "income": 1000},
    "tourism2": {"price": 11000, "income": 2000},
    "tourism3": {"price": 50000, "income": 25000},
    "powerplant": {"price": 25000, "income": 15000},
    "weapons_upgrade": {"price": 10000, "income": 0},
    "missile": {"price": 25000, "income": 0},
    "nuke": {"price": 100000, "income": 0}
}

# -----------------------------
# Background Income Task
# -----------------------------
@tasks.loop(hours=3)
async def give_income():
    data = load_data()
    for country_id in data:
        total_income = data[country_id]["income"]
        data[country_id]["wallet"] += total_income
    save_data(data)
    print("✅ Passive income distributed!")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    give_income.start()

# -----------------------------
# Economy Commands
# -----------------------------
@bot.command()
async def create_country(ctx, *, name):
    role = discord.utils.get(ctx.guild.roles, name="President")
    if role not in ctx.author.roles:
        return await ctx.send("❌ You must have the 'President' role to create a country!")

    data = load_data()
    if str(ctx.author.id) in data:
        return await ctx.send("❌ You already own a country!")

    data[str(ctx.author.id)] = {
        "name": name,
        "wallet": 1000,
        "income": 100,
        "items": {}
    }
    save_data(data)
    await ctx.send(f"🌍 Country **{name}** created with 1000 coins and 100 base income!")

@bot.command()
async def balance(ctx, member: discord.Member=None):
    if member is None:
        member = ctx.author
    data = load_data()

    if str(member.id) not in data:
        return await ctx.send("❌ This user has no country!")

    country = data[str(member.id)]
    embed = discord.Embed(title=f"🌍 {country['name']} Economy", color=discord.Color.gold())
    embed.add_field(name="Wallet 💰", value=country["wallet"])
    embed.add_field(name="Income (per 3h) 📈", value=country["income"])
    embed.add_field(name="Items 🏗️", value=", ".join(country["items"].keys()) or "None")
    await ctx.send(embed=embed)

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Global Shop", color=discord.Color.green())
    for item, data_item in shop_items.items():
        embed.add_field(
            name=item.capitalize(),
            value=f"Price: {data_item['price']} | Income: +{data_item['income']}/3h",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    data = load_data()
    if str(ctx.author.id) not in data:
        return await ctx.send("❌ You must create a country first!")

    item = item.lower()
    if item not in shop_items:
        return await ctx.send("❌ Item not found in shop!")

    country = data[str(ctx.author.id)]
    price = shop_items[item]["price"]
    income = shop_items[item].get("income", 0)

    if country["wallet"] < price:
        return await ctx.send("❌ Not enough money!")

    country["wallet"] -= price
    country["income"] += income
    country["items"][item] = country["items"].get(item, 0) + 1
    save_data(data)

    await ctx.send(f"✅ Bought **{item}**! Income increased by {income}.")

@bot.command()
async def leaderboard(ctx):
    data = load_data()
    leaderboard = sorted(data.items(), key=lambda x: x[1]["wallet"], reverse=True)

    embed = discord.Embed(title="🏆 Richest Countries Leaderboard", color=discord.Color.blue())
    for i, (user_id, country) in enumerate(leaderboard[:10]):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{i+1}. {country['name']} ({user.name})",
            value=f"💰 {country['wallet']} | 📈 {country['income']}/3h",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ Amount must be greater than 0!")

    data = load_data()

    if str(ctx.author.id) not in data:
        return await ctx.send("❌ You must create a country first!")
    if str(member.id) not in data:
        return await ctx.send("❌ That user has no country!")

    sender = data[str(ctx.author.id)]
    receiver = data[str(member.id)]

    if sender["wallet"] < amount:
        return await ctx.send("❌ You don't have enough money!")

    sender["wallet"] -= amount
    receiver["wallet"] += amount
    save_data(data)

    await ctx.send(f"✅ Transferred {amount} coins from **{sender['name']}** to **{receiver['name']}**!")

# -----------------------------
# Admin Commands
# -----------------------------
def is_admin(member):
    return any(r.name == admin_name for r in member.roles)

@bot.command()
async def countries(ctx):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not allowed to use this command!")

    data = load_data()
    msg = ""
    for uid, info in data.items():
        msg += f"**{info['name']}** (Owner: <@{uid}>)\n💰 {info['wallet']} | 📈 {info['income']}/3h\n\n"
    if msg == "":
        msg = "No countries exist yet."
    await ctx.send(msg)

@bot.command()
async def edit_country(ctx, user: discord.Member, field: str, value: int):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not allowed to use this command!")

    data = load_data()
    if str(user.id) not in data:
        return await ctx.send("❌ That user has no country!")

    if field.lower() not in ["wallet", "income"]:
        return await ctx.send("❌ You can only edit 'wallet' or 'income'!")

    data[str(user.id)][field.lower()] = value
    save_data(data)
    await ctx.send(f"✅ Edited {user.name}'s {field} to {value}.")

@bot.command()
async def delete_country(ctx, user: discord.Member):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not allowed to use this command!")

    data = load_data()
    if str(user.id) not in data:
        return await ctx.send("❌ That user has no country!")

    del data[str(user.id)]
    save_data(data)
    await ctx.send(f"🗑️ Deleted {user.name}'s country.")

@bot.command()
async def add_balance(ctx, user: discord.Member, amount: int):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not allowed to use this command!")

    if amount <= 0:
        return await ctx.send("❌ Amount must be greater than 0!")

    data = load_data()
    if str(user.id) not in data:
        return await ctx.send("❌ That user has no country!")

    data[str(user.id)]["wallet"] += amount
    save_data(data)
    await ctx.send(f"✅ Added {amount} coins to **{data[str(user.id)]['name']}**!")

@bot.command()
async def remove_balance(ctx, user: discord.Member, amount: int):
    if not is_admin(ctx.author):
        return await ctx.send("❌ You are not allowed to use this command!")

    if amount <= 0:
        return await ctx.send("❌ Amount must be greater than 0!")

    data = load_data()
    if str(user.id) not in data:
        return await ctx.send("❌ That user has no country!")

    if data[str(user.id)]["wallet"] < amount:
        return await ctx.send("❌ User doesn't have that much money!")

    data[str(user.id)]["wallet"] -= amount
    save_data(data)
    await ctx.send(f"✅ Removed {amount} coins from **{data[str(user.id)]['name']}**!")

@bot.command(name="cmds")
async def cmds(ctx):
    embed = discord.Embed(title="📜 Economy Bot Commands", color=discord.Color.blue())
    embed.add_field(name="!create_country <name>", value="Create your own country (needs President role)", inline=False)
    embed.add_field(name="!balance [@user]", value="Check your or another user's country balance", inline=False)
    embed.add_field(name="!shop", value="View the global shop", inline=False)
    embed.add_field(name="!buy <item>", value="Buy an item from the shop", inline=False)
    embed.add_field(name="!leaderboard", value="Show richest countries", inline=False)
    embed.add_field(name="!transfer @user <amount>", value="Transfer money to another country", inline=False)

    if is_admin(ctx.author):
        embed.add_field(name="👑 Admin Commands", value="(Visible only to Admin role)", inline=False)
        embed.add_field(name="!countries", value="See all countries and stats", inline=False)
        embed.add_field(name="!edit_country @user <wallet/income> <value>", value="Edit a country's wallet or income", inline=False)
        embed.add_field(name="!delete_country @user", value="Delete a country", inline=False)
        embed.add_field(name="!add_balance @user <amount>", value="Add coins to a country's wallet", inline=False)
        embed.add_field(name="!remove_balance @user <amount>", value="Remove coins from a country's wallet", inline=False)

    await ctx.send(embed=embed)

# -----------------------------
# Run Bot
# -----------------------------
bot.run("MTQxMDI2NTY4MDY3ODQ5MDIyNg.GdjqbI.coo92ARK2pNl46pyUxVWm8ylUGIOnCwev6hGwk")
