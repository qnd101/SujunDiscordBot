import discord
from discord.ext import tasks
import asyncio
import yaml
import mc_manager
import time
import gyuhwasays
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from os.path import join
import random
import subprocess
import alchemy
import csv
import shutil

# Intents setup (optional, if you need to access certain features like member events)
intents = discord.Intents.default()
intents.message_content = True
# Bot prefix setupW
bot = discord.Client(intents=intents)

gs_commands = None

with open('./bot_settings.yml', 'r') as file:
    settings = yaml.safe_load(file)["settings"]

mc_settings = settings["mc-manage"]
mc_loaded = False
mc_status = ""
mcsrv = None

cmd_reserved = {"/마크": "마인크래프트 서버에 관한 명령어입니다. /마크 켜: 서버를 켭니다",
                "/명령어": "명령어 목록을 보여줍니다. /명령어 자세히: 명령어에 대한 자세한 설명을 보여줍니다",
                "/재로딩": "명령어 목록을 갱신합니다. 관리자만 사용 가능합니다.",
                "/조합": "두 아이템을 조합합니다. 조합한 적이 있는 아이템만 조합할 수 있습니다. 조합에 성공하면 수준이 올라갑니다.",
                "/조합법": "제작한 적 있는 아이템의 조합법을 보여줍니다.",
                "/남은조합": "해당 아이템에 대해 몇개의 조합법이 남았는지 알려줍니다.",
                "/아이템": "조합한 적이 있는 아이템을 보여줍니다. 더 이상 조합법이 없는 아이템은 표시하지 않습니다.",
                "/크레딧": "현재 크레딧을 보여줍니다.",
                "/랭킹": "크레딧의 랭킹을 보여줍니다.",}
cmd_dict = cmd_reserved.copy()

command_lock = asyncio.Lock() #I need to execute commands synchronously...
font = ImageFont.truetype("./NotoSansKR-Regular.ttf" or "arial.ttf", 20)

with open(settings["credits-path"], newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    credits = {int(row[0]):int(row[1]) for row in reader}

alchemy_config = settings["alchemy-config"]
alchemy_manager = alchemy.Alchemy(alchemy_config["items-path"], alchemy_config["recipes-path"])

#dictionary of item name : userid
shutil.copy(alchemy_config["founditems-path"], alchemy_config["founditems-backuppath"])
with open(alchemy_config["founditems-path"], newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    alchemy_founditems = {row[0]: [int(row[1]), 0] for row in reader}

def new_craftables(item):
    global alchemy_manager, alchemy_founditems
    return sum(1 for item in alchemy_manager.craftable_items(item) if item not in alchemy_founditems)
    
#add a new column representing the number of new craftables
for key in alchemy_founditems.keys():
    craftables = alchemy_manager.craftable_items(key)
    alchemy_founditems[key] = [alchemy_founditems[key][0], new_craftables(key)]

def load_mc():
    global mc_loaded, mcsrv
    if mc_loaded:
        return
    mc_loaded = True
    subprocess.run(["/bin/bash", mc_settings["load-script-path"]], capture_output=True, text=True)
    mcsrv = mc_manager.new(mc_settings["pause-time"], 
                    mc_settings["cool-time"],
                    mc_settings["start-script-path"],
                    mc_settings["backup-script-path"])

def load_gs_config():
    global gs_commands, cmd_dict
    with open(settings["gyuhwasays-config"], 'r') as file:
        gs_settings = yaml.safe_load(file)["settings"]
    gs_dir = gs_settings["imgdir"]
    gs_commands = gs_settings["commands"]
    for cmd_data in gs_commands:
        for data in cmd_data["data"]:
            data["img"] = Image.open(join(gs_dir, data["file"]))

    cmd_dict = cmd_reserved | {cmd_data["cmd"] : f"{len(cmd_data['data'])}개의 사진 중 하나를 무작위로 선정" for cmd_data in gs_commands} | {cmd_data["cmd"]+"[i]" : f"{len(cmd_data['data'])}개의 사진 중 i번째 사진을 선정" for cmd_data in gs_commands}

load_gs_config()

def format_list(li, col_cnt = 5, spacing = 10):
    return "\n".join("".join(s.ljust(spacing) for s in li[i:i+col_cnt]) for i in range(0, len(li), col_cnt) )

@bot.event
async def on_message(message : discord.Message):
    global mcsrv, mc_status, settings, mc_settings
    global cmd_dict
    global gs_commands
    global alchemy_config, alchemy_founditems, alchemy_manager, credits

    async with command_lock:
        content_split = message.content.split()        
        if len(content_split) == 0:
            return
        command = content_split[0]
        
        match command:
            case "/마크":
                if message.channel.id != mc_settings["channel-id"] or message.author == bot.user:
                    return
                if len(content_split) == 1:
                    if not mc_loaded:
                        await message.reply(content="데이터가 아직 로드되지 않았습니다. /마크 켜 명령어를 사용하면 서버를 로드한 후 켭니다.")
                    else:
                        await message.reply(content=mc_status)
                elif content_split[1] == "켜":
                    if not mc_loaded:
                        await message.reply(content="먼저 데이터를 로드합니다. 잠시만 기다려주세요.")
                        load_mc()
                        await message.reply(content="데이터를 로드했습니다.")
                    result = mc_manager.start(mcsrv)
                    await message.reply(content="서버 켜는중..." if result == 0 else f"서버를 켤 수 없음. 에러코드 {result}")
            case "/명령어":
                if len(content_split)>1 and content_split[1] == "자세히":
                    await message.reply(content="\n".join([f"{k}: {v}" for k, v in cmd_dict.items()]))
                else:
                    await message.reply(content=" ".join(cmd_dict.keys()))
            case "/재로딩":
                if message.author.id == settings["admin-id"]:
                    load_gs_config()
                    await message.reply(content="명령어 목록을 갱신했습니다.")
                else:
                    await message.reply(content="권한이 없습니다.")
            case "/조합":
                if len(content_split) != 3:
                    await message.reply(content="아이템 2개를 입력해주세요.")
                    return
                for ing in content_split[1:]:
                    if not alchemy_manager.val_item(ing) or ing not in alchemy_founditems.keys():
                        await message.reply(content=f"'{ing}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                        return
                result = alchemy_manager.combine(content_split[1], content_split[2])
                if len(result) == 0:
                    return
                ing1_em = content_split[1]+alchemy_manager.get_emoji(content_split[1])
                ing2_em = content_split[2]+alchemy_manager.get_emoji(content_split[2])
                for found in result:
                    found_em = found+alchemy_manager.get_emoji(found)
                    
                    if found in alchemy_founditems.keys():
                        found_user = await bot.fetch_user(alchemy_founditems[found][0])
                        msg = f"'{found_em}' 은(는) {found_user} 이(가) 먼저 찾았어요..."
                        color = discord.Color.red()
                        title = "조합 성공! 그러나..."
                    else:
                        gain = len(alchemy_founditems) // 20 + 1
                        if message.author.id in credits:
                            credits[message.author.id] += gain
                        else:
                            credits[message.author.id] = gain
                        msg = f"'{found_em}' 을(를) 조합했다! 현재 크레딧: {credits[message.author.id]} YEOP **[+ {gain} YEOP]**"
                        with open(settings["credits-path"], "w", newline="") as f:
                            for key, value in credits.items():
                                f.write(f"{key}, {value}\n")
                        
                        alchemy_founditems[found] = [message.author.id, new_craftables(found)]
                        for ing in alchemy_manager.get_possible_ings(found):
                            if ing in alchemy_founditems:
                                alchemy_founditems[ing][1] -= 1                       

                        with open(alchemy_config["founditems-path"], "a") as f:
                            f.write(f"{found}, {message.author.id}\n")
                        color = discord.Color.green()
                        title = "조합 성공!"
                    embed = discord.Embed(title=title, description=f"{ing1_em} + {ing2_em} = {found_em}", color=color)
                    await message.reply(embed=embed, content=msg)

            case "/남은조합":
                if len(content_split) != 2:
                    await message.reply(content="아이템 1개를 입력해주세요.")
                    return
                item = content_split[1]
                if not alchemy_manager.val_item(item) or item not in alchemy_founditems:
                    await message.reply(content=f"'{item}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                    return
                leftnew = alchemy_founditems[item][1]
                totalcrafts = alchemy_manager.craftable_items(item)
                await message.reply(content=f"{item+alchemy_manager.get_emoji(item)}으로 제작할 수 있는 아이템 {len(totalcrafts)}개 중 {leftnew}개 남았습니다.")
                
            case "/아이템":
                items = [key+alchemy_manager.get_emoji(key) for key, val in alchemy_founditems.items() if val[1] > 0 ]
                for i in range(0, len(items), 150):
                    await message.reply(f"```\n{format_list(items[i:i+150], 6, 10)}\n```")
                await message.reply(f"총 {len(alchemy_manager.items)}개의 아이템 중 {len(alchemy_founditems)}개를 찾았습니다. 이 중 조합법이 남은 아이템들만 표시했습니다.")

            case "/크레딧":
                cred = credits[message.author.id] if message.author.id in credits else 0
                await message.reply(f"현재 크레딧: {cred} YEOP")
            case "/랭킹":
                sortedlist = sorted(credits.items(), key=lambda x: x[1], reverse=True) 
                users = await asyncio.gather(*[bot.fetch_user(tup[0]) for tup in sortedlist])
                ranklist = [s for i in range(len(sortedlist)) for s in (users[i].name, str(sortedlist[i][1]))]
                await message.reply(content="```\n" + format_list(ranklist, 2, 25) + "\n```")

            case "/조합법":
                if len(content_split) != 2:
                    await message.reply(content="아이템 1개를 입력해주세요.")
                    return
                item = content_split[1]
                if not alchemy_manager.val_item(item) or item not in alchemy_founditems:
                    await message.reply(content=f"'{item}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                    return
                recipe = alchemy_manager.get_recipes(item)
                recipe_text = " , ".join(f"{i1+alchemy_manager.get_emoji(i1)} + {i2+alchemy_manager.get_emoji(i2)}" for i1, i2 in recipe if i1 in alchemy_founditems and i2 in alchemy_founditems)
                await message.reply(content=f"'지금까지 알려진 {item+alchemy_manager.get_emoji(item)}' 의 조합법: \n{recipe_text}")
            case default:
                cmd_data = next(filter(lambda x: command.startswith(x["cmd"]), gs_commands), None)
                if cmd_data is None:
                    # global help_msg
                    # await message.reply(content=help_msg)
                    return
                choices = len(cmd_data["data"])
                if len(command) == len(cmd_data["cmd"]):
                    chosen = cmd_data["data"][random.randint(0, choices-1)]
                else:
                    num = command[len(cmd_data["cmd"]):]
                    if num.isdigit() and int(num) <= choices:
                        chosen = cmd_data["data"][int(num)-1]
                    else:
                        return
                text = message.content[len(command):].strip()
                try:
                    result = gyuhwasays.gyuwhasays(text, font, chosen["img"], (chosen["x"], chosen["y"]))
                    with BytesIO() as image_binary:
                        result.save(image_binary, 'JPEG')
                        image_binary.seek(0)
                        image_file = discord.File(fp=image_binary, filename='pil_image.jpg')

                    # Create an embed
                    embed = discord.Embed(title="", description="")
                    embed.set_image(url="attachment://pil_image.jpg")  # Important: Use attachment://

                    # Send the embed and the file
                    await message.reply(file=image_file, embed=embed)
                finally:
                    return
                # if no command matched

@tasks.loop(seconds=mc_settings["update-period"])
async def mcsrv_update():
    global mcsrv, mc_status
    async with command_lock:
        if not mc_loaded:
            return
        channel = bot.get_channel(mc_settings["channel-id"])
        mc_manager.update(mcsrv)
        newstatus = mc_manager.get_status(mcsrv)
        if mc_status != newstatus:
            print(f"status: {mc_status}")
        mc_status = newstatus
        while True:
            player, msg = mc_manager.try_pop_chat(mcsrv)
            if player and msg:
                await channel.send(f"{player}: {msg}")
            else:
                break

@mcsrv_update.before_loop
async def before():
    await bot.wait_until_ready()

# Event: on bot ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    mcsrv_update.start()

# Run the bot with your token
while True:
    try:
        bot.run(settings["token"])
    except Exception as e:
        print(f"Bot encountered an error: {e}")
        print("Retrying in 5 seconds...")
        time.sleep(5)