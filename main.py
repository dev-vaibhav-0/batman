import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread

# Flask app for 24/7 uptime
app = Flask('')

@app.route('/')
def home():
    return "NG Coin Bot is alive! 🎮"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='slavery!', intents=intents, help_command=None)

# Database setup
def init_db():
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0,
                  last_daily TEXT, last_work TEXT, last_hunt TEXT, last_battle TEXT,
                  PRIMARY KEY (user_id, guild_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS pets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER, guild_id INTEGER,
                  pet_name TEXT, rarity TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Pet data
PETS = {
    'Common': ['🐕 Dog', '🐈 Cat', '🐁 Mouse', '🐇 Rabbit', '🐓 Chicken'],
    'Uncommon': ['🦊 Fox', '🦝 Raccoon', '🦨 Skunk', '🦦 Otter', '🦘 Kangaroo'],
    'Rare': ['🦁 Lion', '🐯 Tiger', '🐻 Bear', '🐼 Panda', '🦓 Zebra'],
    'Epic': ['🐉 Dragon', '🦄 Unicorn', '🦅 Eagle', '🦈 Shark', '🦖 T-Rex'],
    'Legendary': ['🔥 Phoenix', '⚡ Thunder Wolf', '❄️ Ice Phoenix', '🌟 Star Dragon', '💀 Ghost King'],
    'Mythic': ['🌌 Cosmic Dragon', '👑 Golden Emperor', '💎 Diamond Beast', '🌈 Rainbow Phoenix', '🎭 Shadow Demon']
}

RARITY_CHANCES = {
    'Common': 40,
    'Uncommon': 30,
    'Rare': 15,
    'Epic': 10,
    'Legendary': 4,
    'Mythic': 1
}

RARITY_COLORS = {
    'Common': 0x808080,
    'Uncommon': 0x00ff00,
    'Rare': 0x0080ff,
    'Epic': 0x8000ff,
    'Legendary': 0xffa500,
    'Mythic': 0xff0080
}

# Hunt animals
HUNT_ANIMALS = [
    ('🦌 Deer', 50, 150),
    ('🐗 Boar', 75, 200),
    ('🦅 Eagle', 100, 250),
    ('🐺 Wolf', 150, 350),
    ('🦁 Lion', 200, 500),
    ('🐻 Bear', 250, 600),
    ('🐉 Dragon', 500, 1000)
]

# Database helper functions
def get_user_balance(user_id, guild_id):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, guild_id, amount):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, guild_id, balance) VALUES (?, ?, 0)', (user_id, guild_id))
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id=? AND guild_id=?', (amount, user_id, guild_id))
    conn.commit()
    conn.close()

def set_balance(user_id, guild_id, amount):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, guild_id, balance) VALUES (?, ?, ?)', (user_id, guild_id, amount))
    conn.commit()
    conn.close()

def check_cooldown(user_id, guild_id, command_type):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute(f'SELECT {command_type} FROM users WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    result = c.fetchone()
    conn.close()
    
    if result and result[0]:
        last_time = datetime.fromisoformat(result[0])
        if command_type == 'last_daily':
            cooldown = timedelta(hours=24)
        elif command_type == 'last_hunt':
            cooldown = timedelta(minutes=30)
        elif command_type == 'last_battle':
            cooldown = timedelta(minutes=15)
        else:
            cooldown = timedelta(hours=1)
            
        if datetime.now() - last_time < cooldown:
            return False, (last_time + cooldown) - datetime.now()
    return True, None

def update_cooldown(user_id, guild_id, command_type):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, guild_id, balance) VALUES (?, ?, 0)', (user_id, guild_id))
    c.execute(f'UPDATE users SET {command_type}=? WHERE user_id=? AND guild_id=?', 
              (datetime.now().isoformat(), user_id, guild_id))
    conn.commit()
    conn.close()

def add_pet(user_id, guild_id, pet_name, rarity):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT INTO pets (user_id, guild_id, pet_name, rarity) VALUES (?, ?, ?, ?)',
              (user_id, guild_id, pet_name, rarity))
    conn.commit()
    conn.close()

def get_user_pets(user_id, guild_id):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT pet_name, rarity FROM pets WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    pets = c.fetchall()
    conn.close()
    return pets

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} is online!')
    await bot.change_presence(activity=discord.Game(name='slavery!help'))

# Help command
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title='🎮 NG Coin Bot Commands', color=0x00ff00)
    embed.add_field(name='💰 Economy', value=
        '`slavery!balance` - Check your NG coins\n'
        '`slavery!daily` - Claim daily reward (500 coins)\n'
        '`slavery!work` - Work for coins (100-300)\n'
        '`slavery!leaderboard` - Server leaderboard', 
        inline=False)
    embed.add_field(name='🎰 Gambling', value=
        '`slavery!coinflip <amount> <heads/tails>` - Flip a coin\n'
        '`slavery!dice <amount> <1-6>` - Roll a dice\n'
        '`slavery!slots <amount>` - Play slots\n'
        '`slavery!roulette <amount> <red/black/green>` - Play roulette\n'
        '`slavery!highlow <amount>` - High-low card game',
        inline=False)
    embed.add_field(name='🥚 Pets', value=
        '`slavery!openegg` - Open an egg (1000 coins)\n'
        '`slavery!pets` - View your pets\n'
        '`slavery!petcount` - Count pets by rarity',
        inline=False)
    embed.add_field(name='🎯 OwO Style Fun', value=
        '`slavery!hunt` - Hunt for animals (30m cooldown)\n'
        '`slavery!battle <@user>` - Battle another user (15m cooldown)\n'
        '`slavery!pray` - Pray for blessings\n'
        '`slavery!curse` - Curse yourself for chaos\n'
        '`slavery!uwu <text>` - UwUify your text',
        inline=False)
    embed.add_field(name='🔨 Moderation', value=
        '`slavery!ban <@user> [reason]` - Ban a user\n'
        '`slavery!kick <@user> [reason]` - Kick a user\n'
        '`slavery!clear <amount>` - Delete messages',
        inline=False)
    embed.add_field(name='⚙️ Utility', value=
        '`slavery!ping` - Check bot latency',
        inline=False)
    await ctx.send(embed=embed)

# Economy commands
@bot.command(name='balance', aliases=['bal', 'coins'])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = get_user_balance(member.id, ctx.guild.id)
    embed = discord.Embed(title=f'💰 {member.display_name}\'s Balance', 
                          description=f'**{bal:,}** NG Coins', color=0xffd700)
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):
    can_claim, time_left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_daily')
    if not can_claim:
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        await ctx.send(f'⏰ You already claimed your daily! Come back in **{hours}h {minutes}m {seconds}s**')
        return
    
    amount = 500
    update_balance(ctx.author.id, ctx.guild.id, amount)
    update_cooldown(ctx.author.id, ctx.guild.id, 'last_daily')
    embed = discord.Embed(title='🎁 Daily Reward Claimed!', 
                          description=f'You received **{amount:,}** NG Coins!', color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name='work')
async def work(ctx):
    can_work, time_left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_work')
    if not can_work:
        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
        await ctx.send(f'⏰ You\'re tired! Rest for **{minutes}m {seconds}s**')
        return
    
    amount = random.randint(100, 300)
    jobs = ['mined some NG ore', 'coded a bot', 'farmed NG crops', 'traded NG stocks', 
            'streamed on NG TV', 'delivered NG packages']
    job = random.choice(jobs)
    
    update_balance(ctx.author.id, ctx.guild.id, amount)
    update_cooldown(ctx.author.id, ctx.guild.id, 'last_work')
    embed = discord.Embed(title='💼 Work Complete!', 
                          description=f'You {job} and earned **{amount:,}** NG Coins!', 
                          color=0x3498db)
    await ctx.send(embed=embed)

@bot.command(name='leaderboard', aliases=['lb', 'top'])
async def leaderboard(ctx):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT user_id, balance FROM users WHERE guild_id=? ORDER BY balance DESC LIMIT 10', 
              (ctx.guild.id,))
    top_users = c.fetchall()
    conn.close()
    
    if not top_users:
        await ctx.send('No users found in the leaderboard!')
        return
    
    embed = discord.Embed(title=f'🏆 {ctx.guild.name} Leaderboard', color=0xffd700)
    medals = ['🥇', '🥈', '🥉']
    
    for idx, (user_id, balance) in enumerate(top_users, 1):
        try:
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)
            medal = medals[idx-1] if idx <= 3 else f'`{idx}.`'
            embed.add_field(name=f'{medal} {user.display_name}', 
                            value=f'{balance:,} NG Coins', inline=False)
        except:
            pass
    
    await ctx.send(embed=embed)

# Gambling commands
@bot.command(name='coinflip', aliases=['cf'])
async def coinflip(ctx, amount: int, choice: str):
    if amount <= 0:
        await ctx.send('❌ Bet amount must be positive!')
        return
    
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    if balance < amount:
        await ctx.send(f'❌ You don\'t have enough NG Coins! You have **{balance:,}**')
        return
    
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await ctx.send('❌ Choose either `heads` or `tails`!')
        return
    
    choice = 'heads' if choice in ['heads', 'h'] else 'tails'
    result = random.choice(['heads', 'tails'])
    
    if choice == result:
        update_balance(ctx.author.id, ctx.guild.id, amount)
        embed = discord.Embed(title='🪙 Coinflip - You Won!', 
                              description=f'The coin landed on **{result}**!\nYou won **{amount:,}** NG Coins!',
                              color=0x00ff00)
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        embed = discord.Embed(title='🪙 Coinflip - You Lost!', 
                              description=f'The coin landed on **{result}**!\nYou lost **{amount:,}** NG Coins!',
                              color=0xff0000)
    
    await ctx.send(embed=embed)

@bot.command(name='dice')
async def dice(ctx, amount: int, guess: int):
    if amount <= 0:
        await ctx.send('❌ Bet amount must be positive!')
        return
    
    if guess < 1 or guess > 6:
        await ctx.send('❌ Guess must be between 1 and 6!')
        return
    
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    if balance < amount:
        await ctx.send(f'❌ You don\'t have enough NG Coins! You have **{balance:,}**')
        return
    
    roll = random.randint(1, 6)
    
    if guess == roll:
        winnings = amount * 5
        update_balance(ctx.author.id, ctx.guild.id, winnings)
        embed = discord.Embed(title='🎲 Dice - You Won!', 
                              description=f'The dice rolled **{roll}**!\nYou won **{winnings:,}** NG Coins! (5x multiplier)',
                              color=0x00ff00)
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        embed = discord.Embed(title='🎲 Dice - You Lost!', 
                              description=f'The dice rolled **{roll}**!\nYou lost **{amount:,}** NG Coins!',
                              color=0xff0000)
    
    await ctx.send(embed=embed)

@bot.command(name='slots')
async def slots(ctx, amount: int):
    if amount <= 0:
        await ctx.send('❌ Bet amount must be positive!')
        return
    
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    if balance < amount:
        await ctx.send(f'❌ You don\'t have enough NG Coins! You have **{balance:,}**')
        return
    
    emojis = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
    slot1, slot2, slot3 = random.choices(emojis, k=3)
    
    msg = await ctx.send(f'🎰 | {emojis[0]} {emojis[1]} {emojis[2]} |')
    await asyncio.sleep(0.5)
    await msg.edit(content=f'🎰 | {slot1} {emojis[1]} {emojis[2]} |')
    await asyncio.sleep(0.5)
    await msg.edit(content=f'🎰 | {slot1} {slot2} {emojis[2]} |')
    await asyncio.sleep(0.5)
    await msg.edit(content=f'🎰 | {slot1} {slot2} {slot3} |')
    
    if slot1 == slot2 == slot3:
        multiplier = 10 if slot1 == '7️⃣' else 5 if slot1 == '💎' else 3
        winnings = amount * multiplier
        update_balance(ctx.author.id, ctx.guild.id, winnings)
        embed = discord.Embed(title='🎰 JACKPOT!', 
                              description=f'**{slot1} {slot2} {slot3}**\nYou won **{winnings:,}** NG Coins! ({multiplier}x)',
                              color=0xffd700)
    elif slot1 == slot2 or slot2 == slot3:
        winnings = amount
        update_balance(ctx.author.id, ctx.guild.id, winnings)
        embed = discord.Embed(title='🎰 Small Win!', 
                              description=f'**{slot1} {slot2} {slot3}**\nYou won **{winnings:,}** NG Coins! (2x)',
                              color=0x00ff00)
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        embed = discord.Embed(title='🎰 You Lost!', 
                              description=f'**{slot1} {slot2} {slot3}**\nYou lost **{amount:,}** NG Coins!',
                              color=0xff0000)
    
    await ctx.send(embed=embed)

@bot.command(name='roulette', aliases=['rl'])
async def roulette(ctx, amount: int, choice: str):
    if amount <= 0:
        await ctx.send('❌ Bet amount must be positive!')
        return
    
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    if balance < amount:
        await ctx.send(f'❌ You don\'t have enough NG Coins! You have **{balance:,}**')
        return
    
    choice = choice.lower()
    if choice not in ['red', 'black', 'green']:
        await ctx.send('❌ Choose either `red`, `black`, or `green`!')
        return
    
    result = random.choices(['red', 'black', 'green'], weights=[47, 47, 6])[0]
    
    if choice == result:
        multiplier = 14 if result == 'green' else 2
        winnings = amount * multiplier
        update_balance(ctx.author.id, ctx.guild.id, winnings)
        color_emoji = '🟢' if result == 'green' else '🔴' if result == 'red' else '⚫'
        embed = discord.Embed(title='🎡 Roulette - You Won!', 
                              description=f'{color_emoji} The ball landed on **{result}**!\nYou won **{winnings:,}** NG Coins! ({multiplier}x)',
                              color=0x00ff00)
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        color_emoji = '🟢' if result == 'green' else '🔴' if result == 'red' else '⚫'
        embed = discord.Embed(title='🎡 Roulette - You Lost!', 
                              description=f'{color_emoji} The ball landed on **{result}**!\nYou lost **{amount:,}** NG Coins!',
                              color=0xff0000)
    
    await ctx.send(embed=embed)

@bot.command(name='highlow', aliases=['hl'])
async def highlow(ctx, amount: int):
    if amount <= 0:
        await ctx.send('❌ Bet amount must be positive!')
        return
    
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    if balance < amount:
        await ctx.send(f'❌ You don\'t have enough NG Coins! You have **{balance:,}**')
        return
    
    card_values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    your_card = random.choice(card_values)
    
    embed = discord.Embed(title='🃏 High-Low Card Game', 
                          description=f'Your card: **{your_card}**\n\nWill the next card be **higher** or **lower**?',
                          color=0x3498db)
    msg = await ctx.send(embed=embed)
    
    await msg.add_reaction('⬆️')
    await msg.add_reaction('⬇️')
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['⬆️', '⬇️'] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
        choice = 'higher' if str(reaction.emoji) == '⬆️' else 'lower'
        
        next_card = random.choice(card_values)
        your_idx = card_values.index(your_card)
        next_idx = card_values.index(next_card)
        
        if (choice == 'higher' and next_idx > your_idx) or (choice == 'lower' and next_idx < your_idx):
            update_balance(ctx.author.id, ctx.guild.id, amount)
            embed = discord.Embed(title='🃏 You Won!', 
                                  description=f'Your card: **{your_card}** → Next card: **{next_card}**\nYou won **{amount:,}** NG Coins!',
                                  color=0x00ff00)
        elif next_idx == your_idx:
            embed = discord.Embed(title='🃏 Push!', 
                                  description=f'Your card: **{your_card}** → Next card: **{next_card}**\nSame card! No one wins.',
                                  color=0xffff00)
        else:
            update_balance(ctx.author.id, ctx.guild.id, -amount)
            embed = discord.Embed(title='🃏 You Lost!', 
                                  description=f'Your card: **{your_card}** → Next card: **{next_card}**\nYou lost **{amount:,}** NG Coins!',
                                  color=0xff0000)
        
        await msg.edit(embed=embed)
    except asyncio.TimeoutError:
        await ctx.send('⏰ Time\'s up! No bet was placed.')

# Pet commands
@bot.command(name='openegg', aliases=['egg'])
async def open_egg(ctx):
    cost = 1000
    balance = get_user_balance(ctx.author.id, ctx.guild.id)
    
    if balance < cost:
        await ctx.send(f'❌ You need **{cost:,}** NG Coins to open an egg! You have **{balance:,}**')
        return
    
    update_balance(ctx.author.id, ctx.guild.id, -cost)
    
    # Egg opening animation
    msg = await ctx.send('🥚 Opening egg...')
    await asyncio.sleep(1)
    await msg.edit(content='🥚 *crack*')
    await asyncio.sleep(1)
    await msg.edit(content='🐣 *CRACK*')
    await asyncio.sleep(1)
    
    # Determine rarity
    roll = random.randint(1, 100)
    cumulative = 0
    selected_rarity = None
    
    for rarity, chance in RARITY_CHANCES.items():
        cumulative += chance
        if roll <= cumulative:
            selected_rarity = rarity
            break
    
    pet = random.choice(PETS[selected_rarity])
    add_pet(ctx.author.id, ctx.guild.id, pet, selected_rarity)
    
    embed = discord.Embed(title='🎉 You Got a Pet!', 
                          description=f'**{pet}**\nRarity: **{selected_rarity}**',
                          color=RARITY_COLORS[selected_rarity])
    await msg.edit(content='', embed=embed)

@bot.command(name='pets', aliases=['inv', 'inventory'])
async def view_pets(ctx, member: discord.Member = None):
    member = member or ctx.author
    pets = get_user_pets(member.id, ctx.guild.id)
    
    if not pets:
        no_pets_msg = "You don't have any pets yet!" if member == ctx.author else f"{member.display_name} doesn't have any pets yet!"
        await ctx.send(no_pets_msg)
        return
    
    # Group pets by rarity
    rarity_groups = {}
    for pet, rarity in pets:
        if rarity not in rarity_groups:
            rarity_groups[rarity] = []
        rarity_groups[rarity].append(pet)
    
    embed = discord.Embed(title=f'🐾 {member.display_name}\'s Pets', 
                          description=f'Total pets: **{len(pets)}**',
                          color=0x9b59b6)
    
    for rarity in ['Mythic', 'Legendary', 'Epic', 'Rare', 'Uncommon', 'Common']:
        if rarity in rarity_groups:
            pets_str = ', '.join(rarity_groups[rarity])
            embed.add_field(name=f'{rarity} ({len(rarity_groups[rarity])})', 
                            value=pets_str, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='petcount', aliases=['pc'])
async def pet_count(ctx, member: discord.Member = None):
    member = member or ctx.author
    pets = get_user_pets(member.id, ctx.guild.id)
    
    if not pets:
        await ctx.send(f'{"You don\'t" if member == ctx.author else f"{member.display_name} doesn\'t"} have any pets yet!')
        return
    
    rarity_counts = {}
    for pet, rarity in pets:
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
    
    embed = discord.Embed(title=f'📊 {member.display_name}\'s Pet Collection', 
                          color=0xe91e63)
    
    for rarity in ['Mythic', 'Legendary', 'Epic', 'Rare', 'Uncommon', 'Common']:
        count = rarity_counts.get(rarity, 0)
        bar = '█' * count + '░' * (10 - min(count, 10))
        embed.add_field(name=rarity, value=f'{bar} **{count}**', inline=False)
    
    await ctx.send(embed=embed)

# OwO Style Commands
@bot.command(name='hunt')
async def hunt(ctx):
    can_hunt, time_left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_hunt')
    if not can_hunt:
        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
        await ctx.send(f'🏹 You\'re still tracking! Wait **{minutes}m {seconds}s**')
        return
    
    msg = await ctx.send('🏹 Searching for animals...')
    await asyncio.sleep(1.5)
    
    if random.randint(1, 100) <= 70:  # 70% success rate
        animal, min_reward, max_reward = random.choice(HUNT_ANIMALS)
        reward = random.randint(min_reward, max_reward)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_hunt')
        
        embed = discord.Embed(title='🎯 Successful Hunt!', 
                              description=f'You found and caught a **{animal}**!\nYou earned **{reward:,}** NG Coins!',
                              color=0x00ff00)
    else:
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_hunt')
        embed = discord.Embed(title='❌ Hunt Failed!', 
                              description='The animal escaped! Better luck next time!',
                              color=0xff0000)
    
    await msg.edit(content='', embed=embed)

@bot.command(name='battle')
async def battle(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send('❌ You can\'t battle yourself!')
        return
    
    if opponent.bot:
        await ctx.send('❌ You can\'t battle bots!')
        return
    
    can_battle, time_left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
    if not can_battle:
        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
        await ctx.send(f'⚔️ You\'re still recovering! Wait **{minutes}m {seconds}s**')
        return
    
    user_balance = get_user_balance(ctx.author.id, ctx.guild.id)
    opp_balance = get_user_balance(opponent.id, ctx.guild.id)
    
    if user_balance < 100:
        await ctx.send('❌ You need at least **100** NG Coins to battle!')
        return
    
    msg = await ctx.send(f'⚔️ {ctx.author.mention} challenges {opponent.mention} to a battle!')
    await asyncio.sleep(1)
    await msg.edit(content=f'⚔️ Battle starting...')
    await asyncio.sleep(1)
    await msg.edit(content=f'💥 **FIGHT!**')
    await asyncio.sleep(1.5)
    
    # Battle calculation
    user_power = random.randint(1, 100) + (user_balance // 100)
    opp_power = random.randint(1, 100) + (opp_balance // 100)
    
    if user_power > opp_power:
        winnings = random.randint(50, 200)
        update_balance(ctx.author.id, ctx.guild.id, winnings)
        update_balance(opponent.id, ctx.guild.id, -min(winnings, opp_balance))
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        
        embed = discord.Embed(title='🏆 Victory!', 
                              description=f'{ctx.author.mention} defeated {opponent.mention}!\nYou won **{winnings:,}** NG Coins!',
                              color=0x00ff00)
    elif opp_power > user_power:
        loss = random.randint(50, 150)
        update_balance(ctx.author.id, ctx.guild.id, -loss)
        update_balance(opponent.id, ctx.guild.id, loss)
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        
        embed = discord.Embed(title='💀 Defeat!', 
                              description=f'{opponent.mention} defeated {ctx.author.mention}!\nYou lost **{loss:,}** NG Coins!',
                              color=0xff0000)
    else:
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        embed = discord.Embed(title='🤝 Draw!', 
                              description='Both fighters are equally matched! No coins exchanged.',
                              color=0xffff00)
    
    await msg.edit(content='', embed=embed)

@bot.command(name='pray')
async def pray(ctx):
    msg = await ctx.send('🙏 Praying to the NG gods...')
    await asyncio.sleep(2)
    
    outcome = random.randint(1, 100)
    
    if outcome <= 50:  # 50% - Small blessing
        reward = random.randint(10, 100)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        messages = [
            f'✨ The gods smiled upon you! You received **{reward:,}** NG Coins!',
            f'🌟 A divine blessing! You gained **{reward:,}** NG Coins!',
            f'🕊️ Your prayers were answered! **{reward:,}** NG Coins appeared!'
        ]
        embed = discord.Embed(title='🙏 Prayer Answered!', 
                              description=random.choice(messages),
                              color=0xffd700)
    elif outcome <= 80:  # 30% - Medium blessing
        reward = random.randint(100, 500)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        embed = discord.Embed(title='🌈 Divine Miracle!', 
                              description=f'The gods bestowed a great blessing!\nYou received **{reward:,}** NG Coins!',
                              color=0xff00ff)
    elif outcome <= 95:  # 15% - Nothing
        messages = [
            'The gods are silent...',
            'Your prayers echo in the void...',
            'Nothing happened... maybe next time?'
        ]
        embed = discord.Embed(title='😶 Silence...', 
                              description=random.choice(messages),
                              color=0x808080)
    else:  # 5% - Mega blessing
        reward = random.randint(500, 2000)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        embed = discord.Embed(title='💫 DIVINE INTERVENTION!', 
                              description=f'⚡ THE GODS HAVE CHOSEN YOU! ⚡\nYou received **{reward:,}** NG Coins!',
                              color=0xffd700)
    
    await msg.edit(content='', embed=embed)

@bot.command(name='curse')
async def curse(ctx):
    msg = await ctx.send('💀 Invoking dark forces...')
    await asyncio.sleep(2)
    
    outcome = random.randint(1, 100)
    
    if outcome <= 40:  # 40% - Lose coins
        loss = random.randint(50, 300)
        balance = get_user_balance(ctx.author.id, ctx.guild.id)
        actual_loss = min(loss, balance)
        update_balance(ctx.author.id, ctx.guild.id, -actual_loss)
        
        messages = [
            f'💀 The curse backfired! You lost **{actual_loss:,}** NG Coins!',
            f'👻 Dark magic consumed your coins! Lost **{actual_loss:,}** NG Coins!',
            f'🌑 The darkness took its toll... **{actual_loss:,}** NG Coins vanished!'
        ]
        embed = discord.Embed(title='💀 Cursed!', 
                              description=random.choice(messages),
                              color=0x8b0000)
    elif outcome <= 70:  # 30% - Gain coins (risky reward)
        reward = random.randint(200, 800)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        
        messages = [
            f'😈 You made a deal with darkness! Gained **{reward:,}** NG Coins!',
            f'🔥 The curse worked in your favor! **{reward:,}** NG Coins!',
            f'👹 Dark powers reward the bold! You got **{reward:,}** NG Coins!'
        ]
        embed = discord.Embed(title='😈 Dark Blessing!', 
                              description=random.choice(messages),
                              color=0x4b0082)
    else:  # 30% - Nothing
        messages = [
            'The curse fizzled out...',
            'Nothing happened. The spirits ignored you.',
            'Your curse was too weak to manifest.'
        ]
        embed = discord.Embed(title='💨 Fizzle...', 
                              description=random.choice(messages),
                              color=0x696969)
    
    await msg.edit(content='', embed=embed)

@bot.command(name='uwu')
async def uwu(ctx, *, text: str = None):
    if not text:
        await ctx.send('❌ Pwease pwovide some text to uwu-ify! OwO')
        return
    
    # UwU conversion
    uwu_text = text
    replacements = {
        'r': 'w', 'R': 'W',
        'l': 'w', 'L': 'W',
        'na': 'nya', 'Na': 'Nya', 'NA': 'NYA',
        'ne': 'nye', 'Ne': 'Nye', 'NE': 'NYE',
        'ni': 'nyi', 'Ni': 'Nyi', 'NI': 'NYI',
        'no': 'nyo', 'No': 'Nyo', 'NO': 'NYO',
        'nu': 'nyu', 'Nu': 'Nyu', 'NU': 'NYU'
    }
    
    for old, new in replacements.items():
        uwu_text = uwu_text.replace(old, new)
    
    # Add random UwU expressions
    expressions = [' OwO', ' UwU', ' >w<', ' ^w^', ' >///<', ' *notices*', ' *blushes*']
    if len(uwu_text) < 100:  # Don't spam on long messages
        uwu_text += random.choice(expressions)
    
    embed = discord.Embed(title='✨ UwU-ified Text', 
                          description=uwu_text,
                          color=0xff69b4)
    await ctx.send(embed=embed)

# Moderation commands
@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason='No reason provided'):
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(title='🔨 Member Banned', 
                              description=f'**{member}** has been banned.\nReason: {reason}',
                              color=0xff0000)
        await ctx.send(embed=embed)
    except:
        await ctx.send('❌ Failed to ban member. Check permissions.')

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason='No reason provided'):
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(title='👢 Member Kicked', 
                              description=f'**{member}** has been kicked.\nReason: {reason}',
                              color=0xff6600)
        await ctx.send(embed=embed)
    except:
        await ctx.send('❌ Failed to kick member. Check permissions.')

@bot.command(name='clear', aliases=['purge'])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0 or amount > 100:
        await ctx.send('❌ Amount must be between 1 and 100!')
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f'✅ Deleted **{len(deleted) - 1}** messages!')
    await asyncio.sleep(3)
    await msg.delete()

# Utility commands
@bot.command(name='ping')
async def ping(ctx):
    embed = discord.Embed(title='🏓 Pong!', 
                          description=f'Latency: **{round(bot.latency * 1000)}ms**',
                          color=0x00ff00)
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You don\'t have permission to use this command!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Missing argument! Use `slavery!help` for command usage.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Invalid argument provided!')
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f'Error: {error}')

# Start the bot with 24/7 uptime
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
