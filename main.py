# main.py — NG Coin Bot with UltraMax Chaos Mode™
import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
import aiohttp
import glob
import shlex

# 24/7 uptime tiny webserver
app = Flask('')
@app.route('/')
def home():
    return "NG Coin Bot is alive! (UltraMax Chaos) 💀"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# ------------------- CONFIG -------------------
# Put real VVVIP discord IDs here
VVVIP_IDS = [
    111111111111111111,  # replace with real IDs
    222222222222222222
]

TENOR_API_KEY = os.environ.get('TENOR_API_KEY')  # optional, for gifs
BOT_TOKEN = os.environ.get('DISCORD_TOKEN')      # required

# bot prefix
PREFIX = 'slavery!'

# UltraMax: maximum chaos verbosity toggles
ULTRAMAX = True
# ------------------------------------------------

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ------------------- DATABASE -------------------
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

# Pet pools + rarities (unchanged)
PETS = {
    'Common': ['🐕 Dog', '🐈 Cat', '🐁 Mouse', '🐇 Rabbit', '🐓 Chicken'],
    'Uncommon': ['🦊 Fox', '🦝 Raccoon', '🦨 Skunk', '🦦 Otter', '🦘 Kangaroo'],
    'Rare': ['🦁 Lion', '🐯 Tiger', '🐻 Bear', '🐼 Panda', '🦓 Zebra'],
    'Epic': ['🐉 Dragon', '🦄 Unicorn', '🦅 Eagle', '🦈 Shark', '🦖 T-Rex'],
    'Legendary': ['🔥 Phoenix', '⚡ Thunder Wolf', '❄️ Ice Phoenix', '🌟 Star Dragon', '💀 Ghost King'],
    'Mythic': ['🌌 Cosmic Dragon', '👑 Golden Emperor', '💎 Diamond Beast', '🌈 Rainbow Phoenix', '🎭 Shadow Demon']
}

RARITY_CHANCES = {'Common':40,'Uncommon':30,'Rare':15,'Epic':10,'Legendary':4,'Mythic':1}
RARITY_COLORS = {'Common':0x808080,'Uncommon':0x00ff00,'Rare':0x0080ff,'Epic':0x8000ff,'Legendary':0xffa500,'Mythic':0xff0080}

HUNT_ANIMALS = [
    ('🦌 Deer', 50, 150),
    ('🐗 Boar', 75, 200),
    ('🦅 Eagle', 100, 250),
    ('🐺 Wolf', 150, 350),
    ('🦁 Lion', 200, 500),
    ('🐻 Bear', 250, 600),
    ('🐉 Dragon', 500, 1000)
]

# ------------------- VVVIP HELPERS -------------------
def is_vvvip(user_id: int) -> bool:
    return user_id in VVVIP_IDS

def vvvip_value():
    return 10**18  # huge but safe integer

# DB helpers with VVVIP overrides
def get_user_balance(user_id, guild_id):
    if is_vvvip(user_id):
        return vvvip_value()
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def update_balance(user_id, guild_id, amount):
    if is_vvvip(user_id):
        # keep a DB record with huge balance so leaderboards can fetch something if needed
        conn = sqlite3.connect('ngcoin.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users (user_id, guild_id, balance, last_daily, last_work, last_hunt, last_battle) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (user_id, guild_id, vvvip_value(), None, None, None, None))
        conn.commit()
        conn.close()
        return
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, guild_id, balance) VALUES (?, ?, 0)', (user_id, guild_id))
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id=? AND guild_id=?', (amount, user_id, guild_id))
    conn.commit()
    conn.close()

def set_balance(user_id, guild_id, amount):
    if is_vvvip(user_id):
        amount = max(amount, vvvip_value())
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, guild_id, balance) VALUES (?, ?, ?)', (user_id, guild_id, amount))
    conn.commit()
    conn.close()

def check_cooldown(user_id, guild_id, command_type):
    if is_vvvip(user_id):
        return True, None
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute(f'SELECT {command_type} FROM users WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    r = c.fetchone()
    conn.close()
    if r and r[0]:
        last_time = datetime.fromisoformat(r[0])
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
    if is_vvvip(user_id):
        return
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, guild_id, balance) VALUES (?, ?, 0)', (user_id, guild_id))
    c.execute(f'UPDATE users SET {command_type}=? WHERE user_id=? AND guild_id=?', (datetime.now().isoformat(), user_id, guild_id))
    conn.commit()
    conn.close()

def add_pet(user_id, guild_id, pet_name, rarity):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('INSERT INTO pets (user_id, guild_id, pet_name, rarity) VALUES (?, ?, ?, ?)', (user_id, guild_id, pet_name, rarity))
    conn.commit()
    conn.close()

def get_user_pets(user_id, guild_id):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT pet_name, rarity FROM pets WHERE user_id=? AND guild_id=?', (user_id, guild_id))
    pets = c.fetchall()
    conn.close()
    return pets

# ------------------- GIF / TENOR HELPERS -------------------
async def fetch_tenor_gif(action: str) -> str:
    # try Tenor
    if TENOR_API_KEY:
        q = f'{action} anime gif'
        url = f'https://g.tenor.com/v1/search?q={q}&key={TENOR_API_KEY}&limit=25'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=8) as r:
                    if r.status == 200:
                        data = await r.json()
                        results = data.get('results', [])
                        if results:
                            item = random.choice(results)
                            media = item.get('media', [])
                            if media:
                                m0 = media[0]
                                for key in ['gif','mediumgif','tinygif','nanogif']:
                                    if key in m0 and 'url' in m0[key]:
                                        return m0[key]['url']
                            if 'itemurl' in item:
                                return item['itemurl']
        except Exception:
            pass
    # fallback to local gifs
    pattern = os.path.join('gifs', action, '*.gif')
    files = glob.glob(pattern)
    if files:
        return f'file://{os.path.abspath(random.choice(files))}'
    return ''  # no gif found

# ------------------- UTILS: CHAOTIC TEXT -------------------
def chaos(text: str) -> str:
    # UltraMax chaos wrappers: sprinkle slang, emojis, skulls
    if not ULTRAMAX:
        return text
    extras = [' 💀', ' fr', ' ngl', ' 😭', ' lol', ' sksksk', ' :flushed:']
    # random prefix/suffix chaos
    prefix = random.choice(['yo', 'ayy', 'bruh', 'lowkey', 'ngl']) + ' '
    suffix = random.choice(extras + [''])
    return f'{prefix}{text}{suffix}'

# ------------------- BOT EVENTS -------------------
@bot.event
async def on_ready():
    print(f'{bot.user} online — UltraMax Chaos engaging 😈')
    await bot.change_presence(activity=discord.Game(name=f'{PREFIX}help | UwU chaos'))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 1) respond when mentioned
    if bot.user in message.mentions:
        try:
            await message.channel.send(chaos(f'aye {message.author.mention}, whassup? throw a command or choke on vibes 💀'))
        except Exception:
            pass

    # 2) support raw owo!prefix messages (so users can use owo!kiss despite bot prefix)
    content = message.content.strip()
    if content.lower().startswith('owo!'):
        # parse: owo!action <args...>
        try:
            rest = content[len('owo!'):].strip()
            if not rest:
                await message.channel.send(chaos('u used owo! but did no action smh 🤡'))
            else:
                parts = shlex.split(rest)
                action = parts[0].lower()
                # try to get mentioned member
                member = None
                if message.mentions:
                    member = message.mentions[0]
                else:
                    # maybe user provided ID or name
                    if len(parts) > 1:
                        maybe = parts[1]
                        # try id
                        if maybe.isdigit():
                            member = message.guild.get_member(int(maybe))
                        else:
                            # try simple name match
                            member = discord.utils.find(lambda m: m.name == maybe or m.display_name == maybe, message.guild.members)
                # dispatch actions
                if action in ('kiss','owo.kiss','owo_kiss'):
                    await _send_action_gif(channel=message.channel, author=message.author, target=member, action='kiss')
                elif action in ('hug','owo.hug','owo_hug'):
                    await _send_action_gif(channel=message.channel, author=message.author, target=member, action='hug')
                elif action in ('kill','owo.kill','owo_kill'):
                    await _send_action_gif(channel=message.channel, author=message.author, target=member, action='kill')
                else:
                    await message.channel.send(chaos(f'unknown owo action `{action}` fr? try `owo!kiss` or `owo!hug` or `owo!kill`'))
        except Exception as e:
            await message.channel.send(chaos(f'wtf error parsing owo command lol ({e})'))
        return  # don't fallthrough to process_commands for raw owo! messages

    # 3) ensure other commands still run
    await bot.process_commands(message)

# helper used by both commands and raw owo! handler
async def _send_action_gif(channel, author, target, action: str):
    # action: kiss/hug/kill
    if target is None:
        await channel.send(chaos('mention someone dumbass 🫠'))
        return
    gif = await fetch_tenor_gif(action)
    # ultra captions
    captions = {
        'kiss': [
            f'{author.display_name} mwah 😚 {target.display_name} got kissed fr',
            f'{author.display_name} sneaks a smooch on {target.display_name} >w<',
            f'{target.display_name} got the drip kiss from {author.display_name} lol'
        ],
        'hug': [
            f'{author.display_name} hugs {target.display_name} tight omg 😭',
            f'{author.display_name} big snuggles {target.display_name} uwu',
            f'{target.display_name} absorbed by {author.display_name} hug energy'
        ],
        'kill': [
            f'{author.display_name} dramatically annihilates {target.display_name} (fun!!) 💥',
            f'{target.display_name} got yeeted by {author.display_name} sksksk',
            f'{author.display_name} served {target.display_name} chaos soup 💀'
        ]
    }
    desc = random.choice(captions.get(action, [f'{author.display_name} does a thing to {target.display_name}']))
    embed = discord.Embed(title=f'{action.upper()} — chaotic vibes', description=chaos(desc), color=0xff69b4 if action=='kiss' else 0xffc0cb if action=='hug' else 0xff4500)
    if gif:
        if gif.startswith('file://'):
            path = gif.replace('file://','')
            try:
                await channel.send(embed=embed, file=discord.File(path))
            except Exception:
                # fallback to just embed if file sending fails
                await channel.send(embed=embed)
        else:
            embed.set_image(url=gif)
            await channel.send(embed=embed)
    else:
        await channel.send(embed=embed)

# ------------------- HELP -------------------
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title='🎮 NG Coin Bot Commands (UltraMax Chaos)', color=0x00ff00)
    embed.add_field(name='💰 Economy', value=
        '`slavery!balance` - Check NG coins\n'
        '`slavery!daily` - Claim daily (500 or VVVIP ∞)\n'
        '`slavery!work` - Work for coins\n'
        '`slavery!leaderboard` - Server leaderboard',
        inline=False)
    embed.add_field(name='🎰 Gambling', value=
        '`slavery!coinflip <amt> <heads/tails>`\n'
        '`slavery!dice <amt> <1-6>`\n'
        '`slavery!slots <amt>`\n'
        '`slavery!roulette <amt> <red/black/green>`\n'
        '`slavery!highlow <amt>`',
        inline=False)
    embed.add_field(name='🥚 Pets', value=
        '`slavery!openegg` - Open an egg (1000)\n'
        '`slavery!pets` - View pets\n'
        '`slavery!petcount` - Count pets',
        inline=False)
    embed.add_field(name='🎯 OwO Fun', value=
        '`slavery!kiss @user` or `owo!kiss @user`\n'
        '`slavery!hug @user` or `owo!hug @user`\n'
        '`slavery!kill @user` or `owo!kill @user` (fun, not real)',
        inline=False)
    embed.add_field(name='🔨 Moderation', value=
        '`slavery!ban <@user> [reason]` — VVVIPs bypass perms\n'
        '`slavery!kick <@user> [reason]` — VVVIPs bypass perms\n'
        '`slavery!clear <amount>`',
        inline=False)
    embed.add_field(name='⚙️ Utility', value='`slavery!ping` — latency', inline=False)
    await ctx.send(embed=embed)

# ------------------- ECONOMY -------------------
@bot.command(name='balance', aliases=['bal','coins'])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = get_user_balance(member.id, ctx.guild.id)
    pretty = '∞' if is_vvvip(member.id) else f'{bal:,}'
    embed = discord.Embed(title=f'💰 {member.display_name} Balance', description=chaos(f'got **{pretty}** NG Coins'), color=0xffd700)
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):
    can_claim, left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_daily')
    if not can_claim:
        seconds = int(left.total_seconds())
        h, m = seconds//3600, (seconds%3600)//60
        await ctx.send(chaos(f'bruh you already claimed. wait {h}h {m}m fr 💀'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_daily')
        await ctx.send(chaos('🎁 VVVIP DAILY: u got infinite coins fr. flexed. 💸💸'))
        return
    amt = 500
    update_balance(ctx.author.id, ctx.guild.id, amt)
    update_cooldown(ctx.author.id, ctx.guild.id, 'last_daily')
    await ctx.send(chaos(f'🎁 daily claimed! u got **{amt:,}** NG Coins ngl'))

@bot.command(name='work')
async def work(ctx):
    can, left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_work')
    if not can:
        seconds = int(left.total_seconds()); m, s = seconds//60, seconds%60
        await ctx.send(chaos(f'you tired fr, chill {m}m {s}s before working again'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('💼 VVVIP JOB: administered the NG overlord stack, infinite coins added. big pog.'))
        return
    amt = random.randint(100,300)
    jobs = ['mined NG ore','coded cursed bot','farmed NG crops','traded NG stocks','streamed NG tv','delivered packages']
    job = random.choice(jobs)
    update_balance(ctx.author.id, ctx.guild.id, amt)
    update_cooldown(ctx.author.id, ctx.guild.id, 'last_work')
    await ctx.send(chaos(f'💼 {job} — earned **{amt:,}** NG Coins lol'))

@bot.command(name='leaderboard', aliases=['lb','top'])
async def leaderboard(ctx):
    conn = sqlite3.connect('ngcoin.db')
    c = conn.cursor()
    c.execute('SELECT user_id, balance FROM users WHERE guild_id=? ORDER BY balance DESC LIMIT 10', (ctx.guild.id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await ctx.send(chaos('no leaderboard data fr. yk empty server vibes'))
        return
    embed = discord.Embed(title=chaos(f'🏆 {ctx.guild.name} Leaderboard'), color=0xffd700)
    medals = ['🥇','🥈','🥉']
    for i, (uid, bal) in enumerate(rows, 1):
        try:
            user = bot.get_user(uid) or await bot.fetch_user(uid)
            display_bal = '∞' if is_vvvip(uid) else f'{bal:,}'
            medal = medals[i-1] if i<=3 else f'`{i}.`'
            embed.add_field(name=f'{medal} {user.display_name}', value=chaos(f'{display_bal} NG Coins'), inline=False)
        except:
            pass
    await ctx.send(embed=embed)

# ------------------- GAMBLING (VVVIP WINS) -------------------
@bot.command(name='coinflip', aliases=['cf'])
async def coinflip(ctx, amount: int, choice: str):
    if amount <= 0:
        await ctx.send(chaos('nope bet must be >0 fr'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('🪙 VVVIP: coinflip auto-win. u blessed with infinite coins. poggers 💀'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < amount:
        await ctx.send(chaos(f'bro you broke — you got **{bal:,}** only'))
        return
    choice_l = choice.lower()
    if choice_l not in ['heads','tails','h','t']:
        await ctx.send(chaos('pick heads or tails fr'))
        return
    picked = 'heads' if choice_l in ['heads','h'] else 'tails'
    result = random.choice(['heads','tails'])
    if picked == result:
        update_balance(ctx.author.id, ctx.guild.id, amount)
        await ctx.send(chaos(f'🪙 coin landed **{result}** — u won **{amount:,}** ngl'))
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        await ctx.send(chaos(f'🪙 coin landed **{result}** — L, u lost **{amount:,}** fr'))

@bot.command(name='dice')
async def dice(ctx, amount: int, guess: int):
    if amount <= 0 or guess<1 or guess>6:
        await ctx.send(chaos('invalid args lol'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('🎲 VVVIP: dice obeys you. infinite coins.'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < amount:
        await ctx.send(chaos(f'no coins bro. you have **{bal:,}**'))
        return
    roll = random.randint(1,6)
    if roll == guess:
        win = amount * 5
        update_balance(ctx.author.id, ctx.guild.id, win)
        await ctx.send(chaos(f'🎲 rolled **{roll}** — W! you got **{win:,}**'))
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        await ctx.send(chaos(f'🎲 rolled **{roll}** — u lost **{amount:,}** tough luck'))

@bot.command(name='slots')
async def slots(ctx, amount: int):
    if amount <= 0:
        await ctx.send(chaos('bet must be positive lol'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('🎰 VVVIP JACKPOT: infinite coins, always wins.'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < amount:
        await ctx.send(chaos(f'no coins — **{bal:,}** only'))
        return
    emojis = ['🍒','🍋','🍊','🍇','💎','7️⃣']
    s1, s2, s3 = random.choices(emojis, k=3)
    msg = await ctx.send(chaos(f'🎰 | {emojis[0]} {emojis[1]} {emojis[2]} |'))
    await asyncio.sleep(0.4); await msg.edit(content=chaos(f'🎰 | {s1} {emojis[1]} {emojis[2]} |'))
    await asyncio.sleep(0.4); await msg.edit(content=chaos(f'🎰 | {s1} {s2} {emojis[2]} |'))
    await asyncio.sleep(0.4); await msg.edit(content=chaos(f'🎰 | {s1} {s2} {s3} |'))
    if s1==s2==s3:
        mult = 10 if s1=='7️⃣' else 5 if s1=='💎' else 3
        win = amount * mult
        update_balance(ctx.author.id, ctx.guild.id, win)
        await ctx.send(chaos(f'🎰 JACKPOT {s1}{s2}{s3} — you won **{win:,}** ({mult}x)'))
    elif s1==s2 or s2==s3:
        win = amount
        update_balance(ctx.author.id, ctx.guild.id, win)
        await ctx.send(chaos(f'🎰 small win {s1}{s2}{s3} — got **{win:,}** back'))
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        await ctx.send(chaos(f'🎰 L {s1}{s2}{s3} — you lost **{amount:,}**'))

@bot.command(name='roulette', aliases=['rl'])
async def roulette(ctx, amount: int, choice: str):
    if amount <= 0:
        await ctx.send(chaos('bet > 0 fr'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('🎡 VVVIP: ball obeys you. infinite coins.'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < amount:
        await ctx.send(chaos(f'no coins — {bal:,}'))
        return
    ch = choice.lower()
    if ch not in ['red','black','green']:
        await ctx.send(chaos('pick red/black/green fr'))
        return
    result = random.choices(['red','black','green'], weights=[47,47,6])[0]
    if ch==result:
        mult = 14 if result=='green' else 2
        win = amount * mult
        update_balance(ctx.author.id, ctx.guild.id, win)
        await ctx.send(chaos(f'🎡 ball landed {result} — you won **{win:,}** ({mult}x)'))
    else:
        update_balance(ctx.author.id, ctx.guild.id, -amount)
        await ctx.send(chaos(f'🎡 ball landed {result} — you lost **{amount:,}**'))

@bot.command(name='highlow', aliases=['hl'])
async def highlow(ctx, amount: int):
    if amount <= 0:
        await ctx.send(chaos('invalid amount lol'))
        return
    if is_vvvip(ctx.author.id):
        update_balance(ctx.author.id, ctx.guild.id, vvvip_value())
        await ctx.send(chaos('🃏 VVVIP: always right. infinite coins'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < amount:
        await ctx.send(chaos(f'nope you have **{bal:,}**'))
        return
    cards = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    your = random.choice(cards)
    embed = discord.Embed(title='🃏 High-Low', description=chaos(f'Your card: **{your}** — react ⬆️ for higher or ⬇️ for lower'), color=0x3498db)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('⬆️'); await msg.add_reaction('⬇️')
    def check(reaction, user): return user==ctx.author and str(reaction.emoji) in ['⬆️','⬇️'] and reaction.message.id==msg.id
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
        choice = 'higher' if str(reaction.emoji)=='⬆️' else 'lower'
        nxt = random.choice(cards)
        if (choice=='higher' and cards.index(nxt)>cards.index(your)) or (choice=='lower' and cards.index(nxt)<cards.index(your)):
            update_balance(ctx.author.id, ctx.guild.id, amount)
            await msg.edit(embed=discord.Embed(title='🃏 You Won!', description=chaos(f'{your} → {nxt} — you got **{amount:,}**'), color=0x00ff00))
        elif nxt==your:
            await msg.edit(embed=discord.Embed(title='🃏 Push', description=chaos(f'{your} → {nxt} — tie, no coins'), color=0xffff00))
        else:
            update_balance(ctx.author.id, ctx.guild.id, -amount)
            await msg.edit(embed=discord.Embed(title='🃏 You Lost', description=chaos(f'{your} → {nxt} — lost **{amount:,}**'), color=0xff0000))
    except asyncio.TimeoutError:
        await ctx.send(chaos("time's up fr"))

# ------------------- PETS -------------------
@bot.command(name='openegg', aliases=['egg'])
async def openegg(ctx):
    cost = 1000
    if is_vvvip(ctx.author.id):
        add_pet(ctx.author.id, ctx.guild.id, random.choice(PETS['Mythic']), 'Mythic')
        await ctx.send(chaos('🎉 VVVIP Pet: u got a MYTHIC pet. big flex.'))
        return
    bal = get_user_balance(ctx.author.id, ctx.guild.id)
    if bal < cost:
        await ctx.send(chaos(f'need **{cost:,}** to open egg — u have **{bal:,}**'))
        return
    update_balance(ctx.author.id, ctx.guild.id, -cost)
    msg = await ctx.send(chaos('🥚 cracking egg...'))
    await asyncio.sleep(1); await msg.edit(content=chaos('🥚 *crack*'))
    await asyncio.sleep(1); await msg.edit(content=chaos('🐣 *CRACK*'))
    await asyncio.sleep(1)
    roll = random.randint(1,100); cum=0; selected=None
    for r,ch in RARITY_CHANCES.items():
        cum+=ch
        if roll<=cum:
            selected=r; break
    pet = random.choice(PETS[selected])
    add_pet(ctx.author.id, ctx.guild.id, pet, selected)
    await msg.edit(content='', embed=discord.Embed(title='🎉 You Got a Pet!', description=chaos(f'**{pet}** — {selected}'), color=RARITY_COLORS[selected]))

@bot.command(name='pets', aliases=['inv','inventory'])
async def view_pets(ctx, member: discord.Member=None):
    member = member or ctx.author
    pets = get_user_pets(member.id, ctx.guild.id)
    if not pets:
        await ctx.send(chaos(f'{member.display_name} got no pets lol'))
        return
    groups = {}
    for pet,rar in pets:
        groups.setdefault(rar,[]).append(pet)
    embed = discord.Embed(title=chaos(f'🐾 {member.display_name} Pets'), description=chaos(f'total: **{len(pets)}**'), color=0x9b59b6)
    for r in ['Mythic','Legendary','Epic','Rare','Uncommon','Common']:
        if r in groups:
            embed.add_field(name=f'{r} ({len(groups[r])})', value=', '.join(groups[r]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name='petcount', aliases=['pc'])
async def petcount(ctx, member: discord.Member=None):
    member = member or ctx.author
    pets = get_user_pets(member.id, ctx.guild.id)
    if not pets:
        await ctx.send(chaos(f'{member.display_name} has zero pets lol'))
        return
    counts = {}
    for _,r in pets:
        counts[r]=counts.get(r,0)+1
    embed = discord.Embed(title=chaos(f'📊 {member.display_name} Pet Collection'), color=0xe91e63)
    for r in ['Mythic','Legendary','Epic','Rare','Uncommon','Common']:
        c = counts.get(r,0)
        bar = '█'*c + '░'*(10-min(c,10))
        embed.add_field(name=r, value=f'{bar} **{c}**', inline=False)
    await ctx.send(embed=embed)

# ------------------- OWO STYLE COMMANDS (command prefix) -------------------
@bot.command(name='kiss', aliases=['owo_kiss','owo.kiss','owo!kiss'])
async def cmd_kiss(ctx, member: discord.Member = None):
    await _send_action_gif(channel=ctx.channel, author=ctx.author, target=member, action='kiss')

@bot.command(name='hug', aliases=['owo_hug','owo.hug','owo!hug'])
async def cmd_hug(ctx, member: discord.Member = None):
    await _send_action_gif(channel=ctx.channel, author=ctx.author, target=member, action='hug')

@bot.command(name='kill', aliases=['owo_kill','owo.kill','owo!kill'])
async def cmd_kill(ctx, member: discord.Member = None):
    await _send_action_gif(channel=ctx.channel, author=ctx.author, target=member, action='kill')

# ------------------- PRAY / CURSE / BATTLE (chaos language) -------------------
@bot.command(name='pray')
async def pray(ctx):
    msg = await ctx.send(chaos('🙏 praying to cursed NG gods...'))
    await asyncio.sleep(2)
    out = random.randint(1,100)
    if out <= 50:
        reward = random.randint(10,100)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        await msg.edit(content='', embed=discord.Embed(title=chaos('🙏 Prayer Answered!'), description=chaos(f'u got **{reward:,}** coins from the void')))
    elif out <= 80:
        reward = random.randint(100,500)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        await msg.edit(content='', embed=discord.Embed(title=chaos('🌈 Divine Miracle!'), description=chaos(f'big blessing **{reward:,}**')))
    elif out <= 95:
        await msg.edit(content='', embed=discord.Embed(title=chaos('😶 Silence...'), description=chaos('the gods ignored u fr')))
    else:
        reward = random.randint(500,2000)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        await msg.edit(content='', embed=discord.Embed(title=chaos('💫 DIVINE INTERVENTION!'), description=chaos(f'UR chosen — **{reward:,}**')))

@bot.command(name='curse')
async def curse(ctx):
    msg = await ctx.send(chaos('💀 summoning sketchy energies...'))
    await asyncio.sleep(2)
    out = random.randint(1,100)
    if out <= 40:
        loss = random.randint(50,300)
        bal = get_user_balance(ctx.author.id, ctx.guild.id)
        actual = min(loss, bal)
        update_balance(ctx.author.id, ctx.guild.id, -actual)
        await msg.edit(content='', embed=discord.Embed(title=chaos('💀 Cursed!'), description=chaos(f'u lost **{actual:,}** coins. rip')))
    elif out <= 70:
        reward = random.randint(200,800)
        update_balance(ctx.author.id, ctx.guild.id, reward)
        await msg.edit(content='', embed=discord.Embed(title=chaos('😈 Dark Blessing!'), description=chaos(f'u gained **{reward:,}** from the void')))
    else:
        await msg.edit(content='', embed=discord.Embed(title=chaos('💨 Fizzle...'), description=chaos('the curse fizzled. big oof')))

@bot.command(name='battle')
async def battle(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send(chaos("can't battle urself bruh"))
        return
    if opponent.bot:
        await ctx.send(chaos("can't battle bots smh"))
        return
    can, left = check_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
    if not can:
        secs = int(left.total_seconds()); m, s = secs//60, secs%60
        await ctx.send(chaos(f'you still tired — wait {m}m {s}s'))
        return
    ub = get_user_balance(ctx.author.id, ctx.guild.id)
    ob = get_user_balance(opponent.id, ctx.guild.id)
    if ub < 100:
        await ctx.send(chaos('need at least 100 coins to brawl fr'))
        return
    msg = await ctx.send(chaos(f'⚔️ {ctx.author.mention} challenged {opponent.mention} — duel of cursed e-girls'))
    await asyncio.sleep(1); await msg.edit(content=chaos('⚔️ battle initializing...')); await asyncio.sleep(1); await msg.edit(content=chaos('💥 FIGHT!'))
    await asyncio.sleep(1.5)
    user_power = random.randint(1,100) + (ub//100)
    opp_power = random.randint(1,100) + (ob//100)
    if is_vvvip(ctx.author.id):
        # force win
        win = random.randint(50,200)
        update_balance(ctx.author.id, ctx.guild.id, win)
        update_balance(opponent.id, ctx.guild.id, -min(win, ob))
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        await msg.edit(content='', embed=discord.Embed(title=chaos('🏆 VVVIP Victory!'), description=chaos(f'{ctx.author.mention} stomped {opponent.mention} — +**{win:,}**')))
        return
    if user_power > opp_power:
        win = random.randint(50,200)
        update_balance(ctx.author.id, ctx.guild.id, win)
        update_balance(opponent.id, ctx.guild.id, -min(win, ob))
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        await msg.edit(content='', embed=discord.Embed(title=chaos('🏆 Victory!'), description=chaos(f'{ctx.author.mention} wrecked {opponent.mention} — +**{win:,}**')))
    elif opp_power > user_power:
        loss = random.randint(50,150)
        update_balance(ctx.author.id, ctx.guild.id, -loss)
        update_balance(opponent.id, ctx.guild.id, loss)
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        await msg.edit(content='', embed=discord.Embed(title=chaos('💀 Defeat!'), description=chaos(f'{opponent.mention} out-buffed {ctx.author.mention} — -**{loss:,}**')))
    else:
        update_cooldown(ctx.author.id, ctx.guild.id, 'last_battle')
        await msg.edit(content='', embed=discord.Embed(title=chaos('🤝 Draw!'), description=chaos('tie — no coins exchanged')))

# ------------------- MODERATION (VVVIP override) -------------------
@bot.command(name='ban')
async def ban(ctx, member: discord.Member, *, reason='No reason provided'):
    if not (ctx.author.guild_permissions.ban_members or is_vvvip(ctx.author.id)):
        await ctx.send(chaos("u lack perms fr"))
        return
    try:
        await member.ban(reason=reason)
        await ctx.send(chaos(f'🔨 banned {member.display_name} — {reason}'))
    except Exception as e:
        await ctx.send(chaos(f'fail to ban — check bot perms ({e})'))

@bot.command(name='kick')
async def kick(ctx, member: discord.Member, *, reason='No reason provided'):
    if not (ctx.author.guild_permissions.kick_members or is_vvvip(ctx.author.id)):
        await ctx.send(chaos("u lack perms fr"))
        return
    try:
        await member.kick(reason=reason)
        await ctx.send(chaos(f'👢 kicked {member.display_name} — {reason}'))
    except Exception as e:
        await ctx.send(chaos(f'fail to kick — check bot perms ({e})'))

@bot.command(name='clear', aliases=['purge'])
async def clear(ctx, amount: int):
    if not (ctx.author.guild_permissions.manage_messages or is_vvvip(ctx.author.id)):
        await ctx.send(chaos("u lack perms fr"))
        return
    if amount <= 0 or amount > 100:
        await ctx.send(chaos('amount must be 1-100'))
        return
    try:
        deleted = await ctx.channel.purge(limit=amount+1)
        m = await ctx.send(chaos(f'✅ deleted {len(deleted)-1} msgs'))
        await asyncio.sleep(2); await m.delete()
    except Exception as e:
        await ctx.send(chaos(f'fail to purge ({e})'))

# ------------------- UTIL -------------------
@bot.command(name='ping')
async def ping(ctx):
    ms = round(bot.latency * 1000)
    await ctx.send(chaos(f'🏓 pong — {ms}ms ngl'))

# ------------------- ERRORS -------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(chaos("u don't have permission bruh"))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(chaos(f'missing arg — use {PREFIX}help'))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(chaos('bad arg provided ngl'))
    elif isinstance(error, commands.CommandNotFound):
        # silent for unknown commands
        return
    else:
        print('ERR:', error)

# ------------------- START -------------------
if not BOT_TOKEN:
    print('ERROR: set DISCORD_TOKEN env var')
else:
    keep_alive()
    bot.run(BOT_TOKEN)
