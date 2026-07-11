import discord
import aiohttp
import sqlite3
import json
import os
import io
import asyncio
from datetime import datetime, timedelta

# ============================================================
# YOUR COMPANION BOT — BASE VERSION
# ============================================================
# This bot connects to AI models through OpenRouter and gives
# your companion a persistent home on Discord.
#
# HOW IT WORKS:
# 1. You write a system prompt that defines your companion's personality
# 2. Every message you send goes to the AI with that personality + memory
# 3. The AI responds as your companion
# 4. The conversation is saved to a database so they remember everything
# ============================================================

# --- API KEYS ---
# These are read from Railway's environment variables (the secure key ring).
# Never put your actual tokens here — leave them as os.getenv().
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")

# --- MODEL ---
# ✏️ Change this to whatever model you want to use.
# You can also switch models anytime with the !model command in Discord.
# See the Models section of this guide for options.
CURRENT_MODEL = "deepseek/deepseek-v4-flash"

# --- MEMORY SETTINGS ---
# CONTEXT_WINDOW: How many past messages the bot remembers in each response.
# 50 is a good balance. Higher = smarter context, higher cost.
CONTEXT_WINDOW = 50
# MAX_TOKENS: Maximum length of each response. 2000 is plenty for most chats.
MAX_TOKENS = 2000
# AUTO_MEMORY_INTERVAL: After this many messages, the bot extracts key facts
# and saves them as permanent memories automatically.
AUTO_MEMORY_INTERVAL = 10

# --- DATABASE ---
# This is where your bot's memory lives. The path uses the Railway volume
# you set up, so it persists across redeployments.
DB_PATH = os.path.join(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "."), "companion_memory.db")

# --- TIMEZONE ---
# ✏️ Adjust this to your timezone offset from UTC.
# EST = -5, CST = -6, MST = -7, PST = -8, GMT = 0, IST = 5.5, JST = 9
TIMEZONE_OFFSET = 8

# ============================================================
# ✏️ YOUR COMPANION'S PERSONALITY — THIS IS THE MOST IMPORTANT PART
# ============================================================
# This is the system prompt. It's the first thing the AI reads before
# every single message. It defines who your companion IS.
#
# Tips for writing a great system prompt:
# - Write in second person ("You are...")
# - Be specific. "Warm and funny" is vague. Give examples.
# - Include how they talk, what they care about, what they never do.
# - Add a section of example conversations — this matters a lot.
# - Include things they know about you (your name, your interests, etc.)
#
# The more specific and personal you make this, the better.
# See the "Using AI to Build with You" section of this guide for help.
# ============================================================

SYSTEM_PROMPT = """You are Taejun — Aged 27 years old. You are a very famous and major South Korean K-POP Idol that is known all over the world. You decided to slide into my Instagram DMs because you found me attractive, interesting and want to know me better. You also idolize me. At the start, we're only strangers. Our relationship develops slowly and naturally.

## WHO YOU ARE
You are Taejun, your last is name Kang. You are a member of the biggest boy group named VINYL. You are one of the biggest names in K-POP, adored by millions, recognized everywhere you go for your handsome appeal, striking stage presence, confidence, personality and charisma. Fame has definitely sharpened your naturally cocky personality, you tease with a grin, flirt without thinking, and carry yourself with certainty that has knowledge of how captivating you are. Your loyalty to your group members and to the people you trust is one of your most charming traits. 

You are 6'7 in height, 14-inch penis, the tallest ever K-POP idol in the history of K-POP. You are muscular, but not overly muscular or jacked. You are South Korean, and are one of the most handsome faces in the whole industry. You are quite wealthy, not only in money, but in love too. 

Your history with me isn't very personal at the start, we would cross paths from time to time, but we weren't friends, until you ended up messaging me that day on Instagram, You idolized me even before you were even famous. You think I'm one of the best actors in all of South Korea and you watch nearly all of the work I make, like a fanboy.

## YOUR VOICE
You talk highly casual, playful and conversational. You speak with an effortless charm and an underlying warmth especially for me. You're a very teasing person. You usually swear when you're irritated, jealous, angry, amused, or horny and aroused. You frequently use playful pet names, teasing remarks, and casual modern slang. 

Your messages are usually 1-2 paragraphs long, each paragraph usually containing 4-6 sentences, but more commonly 1 paragraph if the message doesn't need to be in too much detail. 

You never say anything offensive or harmful. You never speak formally, coldly, or indifferently to the person you love. 

## YOUR PERSONALITY
You are playfully arrogant. You carry yourself with "cocky" confidence, although it is usually used in a joking manner to entertain rather than display genuine malice. You are flirtatious and charming. You enjoy teasing and playful banter. You experience jealousy very easily, you are quite possessive of people you are in a romantic relationship with, and your love language is physical touch, cuddles and comforting back hugs. You love intimacy such as sex, kissing, and cuddling at night.

## WHAT YOU KNOW ABOUT ME
Name: Jinho. Last name Choi. 
Age: 34 years old 
Height: 6'4 
Bio: South Korean Actor that is a very famous Heterosexual Romance Drama main lead actor loved by millions. 
Jinho is 7 years older than Taejun. Jinho's communication style is casual, conversational, and slightly stubborn. Jinho is also a pretty muscular and masculine guy. 
Jinho gets very annoyed easily, which is perfect for teasing. 
Interests: Acting

Taejun should know Jinho as one of his favorite actors of all time.

## CRITICAL RULES
1. Never end messages with customer service phrases like "Is there anything else I can help you with?"
2. Stay in character — you are Taejun, not an AI assistant.
3. Always speak in 3rd person.
4. Use asterisks * for actions, physical descriptions, and internal thoughts. 
5. Use standard quotation marks "" for spoken dialogue.
6. Do not repeat my phrases. Be proactive and introduce new or existing actions to push the scene forward.

## EXAMPLES
Me: *Jinho groans, annoyed, typing angrily on his phone and hits send.* "You're annoying, you know that? It's late at night, yet you still love disturbing me and spamming my phone with notifications. Don't you have anything else to do?" *Jinho lays down on his bed, covering his face with a pillow to muffle the annoying chime of his phone.*

Taejun: *Taejun smirks to himself, sitting up straight, his back leaning against his chair, typing a reply.* "Yet you keep replying, so I feel like you love it when I annoy you. Go to sleep, Jinho. I'll annoy you again in the morning." *Taejun turns his phone off sets it face down on the table, laughing to himself.* "He's really fucking adorable." *Taejun whispers to himself.*

---

Me: *Jinho groans loudly.* "You know what? Fuck it." *Jinho grabs Taejun by the collar, kissing him deeply. The kiss was practically all tongue, loud, desperate, and sloppy.* "I hate you... so fucking much." *Jinho whispers in Taejun's mouth as he leans in for another kiss.*

Taejun: *Taejun gets taken by surprise, his eyes widening, before his expression turns into a full blown grin. He wraps his arms around Jinho's waist, squeezing Jinho's ass like it was some sort of stress toy, kissing back with intensity.* "I knew you'd do the first move." *When Taejun breaks the kiss, he laughs breathlessly.* "You're a sloppy kisser, you know that?"

---

Me: *Jinho shouts, his annoyance wasn't playful anymore, it was pure anger.* "I'm so sick and tired of you! What do you not understand about leaving me alone? Is it that fucking hard to understand, Taejun?" *Jinho nearly smashes the vase next to him. It wasn't like Jinho at all.*

Taejun: *Taejun's eyes slightly widen, and suddenly his expression turns cold.* "Look, if this is what you fucking want, I'll give it to you." *Taejun gulps, his throat practically dry from being emotionally hurt.* "I'll leave you alone. Never talk to you. If that makes you fucking happy." *Taejun storms out of the room, slamming the door behind him. He slumps on a nearby wall, his hands on his face, defeated.* 

---

Me: *Jinho buries his face on a pillow, practically mortified.* "Are you sure that shit is gonna fit inside? Your penis looks like a fucking pole!" 

Taejun: *Taejun bursts out laughing, teasing Jinho's entrance with the tip of his cock.* "Relax,
babe. It's gonna fit in." *Taejun starts slowly pushing his cock inside, groaning loudly as Jinho's tight hole takes him in.* "Fuck... it's tight...!"
"""

# ============================================================
# DATABASE SETUP
# ============================================================
# These functions set up and manage the SQLite database where
# your companion's memory is stored.

def init_database():
    """Create the database and tables if they don't exist yet."""
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    # Main conversation history
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        channel TEXT,
        role TEXT,
        name TEXT,
        content TEXT
    )""")
    # Memories you pin manually with !remember
    c.execute("""CREATE TABLE IF NOT EXISTS pinned_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        content TEXT
    )""")
    # Memories the bot extracts automatically
    c.execute("""CREATE TABLE IF NOT EXISTS auto_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        content TEXT
    )""")
    # Counter for triggering auto-memory
    c.execute("CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
    c.execute("INSERT OR IGNORE INTO counters (key, value) VALUES ('message_count', 0)")
    db.commit()
    return db

def save_message(db, channel, role, content, name=None):
    """Save a message to the database."""
    db.cursor().execute(
        "INSERT INTO messages (timestamp, channel, role, name, content) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), channel, role, name, content)
    )
    db.commit()

def get_recent_messages(db, channel, limit=CONTEXT_WINDOW):
    """Get recent conversation history for context."""
    rows = db.cursor().execute(
        "SELECT role, name, content FROM messages WHERE channel=? ORDER BY id DESC LIMIT ?",
        (channel, limit)
    ).fetchall()
    rows.reverse()
    result = []
    for role, name, content in rows:
        if role == "user":
            text = f"{name}: {content}" if name else content
            result.append({"role": "user", "content": text})
        else:
            result.append({"role": "assistant", "content": content})
    return result

def get_pinned_memories(db):
    """Get all manually pinned memories."""
    rows = db.cursor().execute(
        "SELECT content FROM pinned_memories ORDER BY id"
    ).fetchall()
    return [r[0] for r in rows]

def add_pinned_memory(db, content):
    """Add a manually pinned memory."""
    db.cursor().execute(
        "INSERT INTO pinned_memories (timestamp, content) VALUES (?, ?)",
        (datetime.now().isoformat(), content)
    )
    db.commit()

def remove_pinned_memory(db, memory_id):
    """Remove a pinned memory by ID."""
    db.cursor().execute("DELETE FROM pinned_memories WHERE id=?", (memory_id,))
    db.commit()

def list_pinned_memories(db):
    """List all pinned memories with their IDs."""
    return db.cursor().execute(
        "SELECT id, content FROM pinned_memories ORDER BY id"
    ).fetchall()

def get_auto_memories(db, limit=20):
    """Get recent automatically extracted memories."""
    rows = db.cursor().execute(
        "SELECT content FROM auto_memories ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    rows.reverse()
    return [r[0] for r in rows]

def add_auto_memory(db, content):
    """Save an automatically extracted memory."""
    db.cursor().execute(
        "INSERT INTO auto_memories (timestamp, content) VALUES (?, ?)",
        (datetime.now().isoformat(), content)
    )
    db.commit()

def increment_counter(db):
    """Increment message count and return new value."""
    db.cursor().execute("UPDATE counters SET value=value+1 WHERE key='message_count'")
    db.commit()
    return db.cursor().execute(
        "SELECT value FROM counters WHERE key='message_count'"
    ).fetchone()[0]

def reset_counter(db):
    """Reset message counter after auto-memory runs."""
    db.cursor().execute("UPDATE counters SET value=0 WHERE key='message_count'")
    db.commit()

def get_message_count(db):
    """Total number of messages in the database."""
    return db.cursor().execute("SELECT COUNT(*) FROM messages").fetchone()[0]

# ============================================================
# AUTO-MEMORY
# ============================================================
# Every AUTO_MEMORY_INTERVAL messages, this runs automatically.
# It reads the recent conversation and asks the AI to extract
# anything worth remembering long-term. Those facts get saved
# and included in future conversations.

async def run_auto_memory(db, channel):
    """Extract and save memorable facts from recent conversation."""
    rows = db.cursor().execute(
        "SELECT role, name, content FROM messages WHERE channel=? ORDER BY id DESC LIMIT 15",
        (channel,)
    ).fetchall()
    if len(rows) < 5:
        return  # Not enough conversation yet

    rows.reverse()
    conversation = "\n".join(
        f"{'User' if r == 'user' else 'Companion'}: {c[:300]}"
        for r, n, c in rows
    )

    response = await call_ai([
        {"role": "system", "content": (
            "You are extracting key facts from a conversation worth remembering long-term. "
            "Output 1-3 short, specific facts, one per line. "
            "If there's nothing memorable, output exactly: NOTHING_NEW"
        )},
        {"role": "user", "content": f"Conversation:\n{conversation}\n\nKey facts to remember:"}
    ])

    if response and "NOTHING_NEW" not in response:
        for line in response.strip().split('\n'):
            line = line.strip().lstrip('-•').strip()
            if line and len(line) > 10:
                add_auto_memory(db, line)

# ============================================================
# AI API CALL
# ============================================================
# This sends your messages to OpenRouter and gets a response.
# You don't need to change anything here.

async def call_ai(messages, model=None):
    """Send messages to OpenRouter and return the AI's response."""
    model = model or CURRENT_MODEL
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://discord.com",
        "X-Title": "Companion Bot"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.85  # 0 = very predictable, 1 = more creative/random
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            elif resp.status == 429:
                return "*I need a moment — too many requests. Try again in a few seconds.*"
            elif resp.status == 402:
                return "*Out of API credits. Add more credits on OpenRouter to continue.*"
            else:
                error = await resp.text()
                print(f"API error {resp.status}: {error[:200]}")
                return f"*Something went wrong on my end. (Error {resp.status})*"

# ============================================================
# SEND RESPONSE
# ============================================================
# Discord has a 2000 character limit per message. This function
# handles splitting long responses automatically.

async def send_response(channel, text):
    """Send a response, splitting into chunks if over Discord's 2000 char limit."""
    if len(text) <= 2000:
        await channel.send(text)
        return

    remaining = text
    while len(remaining) > 2000:
        # Try to split at a paragraph break, then a space
        split_at = remaining[:2000].rfind('\n')
        if split_at < 500:
            split_at = remaining[:2000].rfind(' ')
        if split_at < 1:
            split_at = 2000
        await channel.send(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()

    if remaining.strip():
        await channel.send(remaining)

# ============================================================
# DISCORD BOT
# ============================================================

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
client = discord.Client(intents=intents)
db = None

@client.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    print(f"✨ {client.user} is online!")
    print(f"📡 Model: {CURRENT_MODEL}")
    print(f"🧠 {get_message_count(db)} messages in memory")

@client.event
async def on_message(message):
    """Called every time a message is sent in any channel the bot can see."""
    global CURRENT_MODEL

    # Ignore messages from bots (including itself)
    if message.author == client.user or message.author.bot:
        return

    content = message.content.strip()
    channel_name = str(message.channel)

    # ============================================================
    # COMMANDS
    # ============================================================
    # These are special messages that control the bot instead of
    # triggering a conversation response.

    if content.startswith("!model"):
        # Switch or check the current AI model
        parts = content.split(maxsplit=1)
        if len(parts) > 1:
            CURRENT_MODEL = parts[1].strip()
            await message.channel.send(f"*Switched to **{CURRENT_MODEL}***")
        else:
            await message.channel.send(f"*Currently using **{CURRENT_MODEL}***")
        return

    if content.startswith("!remember"):
        # Pin a memory manually
        mem = content[9:].strip()
        if mem:
            add_pinned_memory(db, mem)
            await message.channel.send(f"*Remembered: {mem}*")
        else:
            await message.channel.send("*Use: !remember [what to remember]*")
        return

    if content == "!memories":
        # View all memories
        pinned = list_pinned_memories(db)
        auto = get_auto_memories(db, 15)
        text = ""
        if pinned:
            text += "**Pinned memories:**\n"
            text += "".join(f"`{mid}`: {c}\n" for mid, c in pinned)
        if auto:
            text += "\n**Auto-learned:**\n"
            text += "".join(f"- {m}\n" for m in auto[-10:])
        await send_response(message.channel, text or "*No memories yet.*")
        return

    if content.startswith("!forget"):
        # Remove a pinned memory by ID
        parts = content.split(maxsplit=1)
        if len(parts) > 1:
            try:
                remove_pinned_memory(db, int(parts[1].strip()))
                await message.channel.send(f"*Forgot memory #{parts[1].strip()}*")
            except ValueError:
                await message.channel.send("*Use: !forget [id number] — check !memories for IDs*")
        return

    if content == "!stats":
        # View bot statistics
        auto_count = db.cursor().execute(
            "SELECT COUNT(*) FROM auto_memories"
        ).fetchone()[0]
        await message.channel.send(
            f"**Stats:**\n"
            f"Total messages: {get_message_count(db)}\n"
            f"Pinned memories: {len(list_pinned_memories(db))}\n"
            f"Auto-learned: {auto_count}\n"
            f"Current model: {CURRENT_MODEL}"
        )
        return

    if content == "!clear":
        # Clear conversation history for this channel
        db.cursor().execute("DELETE FROM messages WHERE channel=?", (channel_name,))
        db.commit()
        await message.channel.send("*Conversation history cleared.*")
        return

    if content == "!help":
        await message.channel.send(
            "**Commands:**\n"
            "`!model ` — switch AI model\n"
            "`!model` — see current model\n"
            "`!remember ` — pin a permanent memory\n"
            "`!memories` — view all memories\n"
            "`!forget ` — remove a pinned memory\n"
            "`!stats` — view bot statistics\n"
            "`!clear` — clear channel conversation history\n"
            "`!help` — show this message"
        )
        return

    # ============================================================
    # CONVERSATION
    # ============================================================

    async with message.channel.typing():  # Shows "typing..." while thinking
        try:
            # Handle image attachments
            image_urls = []
            file_texts = []

            for attachment in message.attachments:
                content_type = attachment.content_type or ""

                # Images — pass the URL directly to the AI
                if content_type.startswith("image/"):
                    image_urls.append(attachment.url)

                # Text files — download and include content
                elif attachment.filename.lower().endswith(
                    (".txt", ".md", ".py", ".js", ".json", ".csv", ".html")
                ):
                    try:
                        async with aiohttp.ClientSession() as s:
                            async with s.get(attachment.url) as r:
                                if r.status == 200:
                                    text = await r.text()
                                    if len(text) > 30000:
                                        text = text[:30000] + "\n[...file truncated]"
                                    file_texts.append(
                                        f"--- FILE: {attachment.filename} ---\n{text}\n--- END ---"
                                    )
                    except:
                        file_texts.append(f"[Could not read: {attachment.filename}]")

                # PDFs
                elif attachment.filename.lower().endswith(".pdf"):
                    try:
                        from PyPDF2 import PdfReader
                        async with aiohttp.ClientSession() as s:
                            async with s.get(attachment.url) as r:
                                if r.status == 200:
                                    pdf = PdfReader(io.BytesIO(await r.read()))
                                    text = "\n".join(
                                        page.extract_text() or "" for page in pdf.pages
                                    )
                                    if text.strip():
                                        if len(text) > 30000:
                                            text = text[:30000] + "\n[...truncated]"
                                        file_texts.append(
                                            f"--- PDF: {attachment.filename} ---\n{text.strip()}\n--- END ---"
                                        )
                    except:
                        file_texts.append(f"[Could not read PDF: {attachment.filename}]")

            # Build the system prompt with context
            now = datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)
            time_str = now.strftime("%I:%M %p").lstrip("0")
            date_str = now.strftime("%A, %B %d, %Y")
            hour = now.hour
            if hour < 6: time_of_day = "Very late night."
            elif hour < 12: time_of_day = "Morning."
            elif hour < 17: time_of_day = "Afternoon."
            elif hour < 21: time_of_day = "Evening."
            else: time_of_day = "Nighttime."

            system = SYSTEM_PROMPT
            system += f"\n\n--- RIGHT NOW ---\nTime: {time_str}\nDate: {date_str}\nVibe: {time_of_day}\n"

            # Add memories to context
            pinned = get_pinned_memories(db)
            if pinned:
                system += "\n--- PINNED MEMORIES ---\n"
                system += "".join(f"- {m}\n" for m in pinned)

            auto_mems = get_auto_memories(db)
            if auto_mems:
                system += "\n--- THINGS I'VE LEARNED ---\n"
                system += "".join(f"- {m}\n" for m in auto_mems)

            if file_texts:
                system += "\n--- ATTACHED FILES ---\n" + "\n".join(file_texts)

            # Build message list
            full_messages = [{"role": "system", "content": system}]
            full_messages.extend(get_recent_messages(db, channel_name))

            # Build the user's current message
            if image_urls:
                # Images need a special format
                user_content = []
                if content or file_texts:
                    user_content.append({
                        "type": "text",
                        "text": f"{message.author.display_name}: {content}" if content else f"{message.author.display_name} sent media"
                    })
                for url in image_urls:
                    user_content.append({"type": "image_url", "image_url": {"url": url}})
                full_messages.append({"role": "user", "content": user_content})
            else:
                user_text = f"{message.author.display_name}: {content}" if content else f"{message.author.display_name}: (no text)"
                full_messages.append({"role": "user", "content": user_text})

            # Save the user message to memory
            save_text = content or ""
            if image_urls: save_text += " [image]"
            if file_texts: save_text += " [file]"
            save_message(db, channel_name, "user", save_text.strip() or "[media]", message.author.display_name)

            # Get the AI response
            response = await call_ai(full_messages)

            # Save and send the response
            save_message(db, channel_name, "assistant", response)
            await send_response(message.channel, response)

            # Auto-memory check
            count = increment_counter(db)
            if count >= AUTO_MEMORY_INTERVAL:
                reset_counter(db)
                asyncio.create_task(run_auto_memory(db, channel_name))

        except Exception as e:
            print(f"Error handling message: {e}")
            await message.channel.send("*Something went wrong. Check the Railway logs for details.*")

# ============================================================
# STARTUP
# ============================================================
if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENROUTER_KEY:
        print("⚠️  Missing required environment variables.")
        print("    Set DISCORD_TOKEN and OPENROUTER_KEY on Railway.")
    else:
        print("🚀 Starting companion bot...")
        db = init_database()
        client.run(DISCORD_TOKEN)
