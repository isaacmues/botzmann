import os
import discord
import time
import datetime
import numpy as np
import matplotlib.pyplot as plt
import scipy.constants as cts
from dotenv import load_dotenv
from discord.ext import tasks
from PIL import Image
from io import StringIO
from contextlib import redirect_stdout

# Command keys
# =========================================================================

tex_cmd = "tex>"
bot_cmd = "bot>"
cts_cmd = "cts>"
ptn_cmd = "python>"

# Configuration for rendering latex
# =========================================================================

plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica"],
    "font.size": 20})

plt.style.use('dark_background')


def latex_render(message):

    output_file = "reply.png"

    fig,ax = plt.subplots(figsize=(3, 2), dpi=300)
    ax.text(0, 0, message.replace(tex_cmd+" ", ""), va="center", ha="center")
    ax.set_xlim(-4,4)
    ax.set_ylim(-1,1)
    ax.axis("off")
    plt.savefig(output_file, transparent=True)

    padding = 20.0
    padding = np.asarray([-1, -1, 1, 1]) * padding

    with Image.open(output_file) as im:
	
        imageBox = im.getbbox()
        imageBox = tuple(np.asarray(imageBox) + padding)
        cropped  = im.crop(imageBox)
        cropped.save(output_file)

#=========================================================================


def find_constant(message):

    constants = cts.find(message.replace(cts_cmd+" ", ""))
    
    if constants != []:

        table = ["{}\t{} {}".format(c, cts.value(c), cts.unit(c)) for c in constants]
        table = "\n".join(table)
        return table

    else:

        return "No hubo resultados"


def pass_to_python(message):

    output = StringIO()

    with redirect_stdout(output):
    
        exec(message.replace(ptn_cmd, ""), {})

    return output.getvalue()

botzmann = discord.Client()

load_dotenv()
token = os.getenv("TOKEN")
admin_id = int(os.getenv("ADMIN_ID"))
server_id = int(os.getenv("SERVER_ID"))
announcements_channel_id = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
class_channel_id = int(os.getenv("CLASS_CHANNEL_ID"))
testing_channel_id = int(os.getenv("TESTING_CHANNEL_ID"))


# Schedule
class_days = ["Mon", "Wed", "Fri"]
start_hour = "09:50"
end_hour = "12:10"
tolerance = datetime.timedelta(minutes=40)

# For Testing
if False:
    class_days.append(time.strftime("%a"))
    start_hour = datetime.datetime.now() + datetime.timedelta(minutes=1)
    end_hour = start_hour + datetime.timedelta(minutes=2)
    start_hour = start_hour.strftime("%H:%M")
    end_hour = end_hour.strftime("%H:%M")


def is_not_holiday():

    today = time.strftime("%d %b")

    holidays = [line.strip() for line in open("holidays.txt", "r")]

    return not (today in holidays)


def is_class_starting(class_days, start_hour):

    now = time.strftime("%H:%M")
    today = time.strftime("%a")

    return (today in class_days) and (now == start_hour) and is_not_holiday()


def is_class_ending(class_days, end_hour):

    now = time.strftime("%H:%M")
    today = time.strftime("%a")

    return (today in class_days) and (now == end_hour) and is_not_holiday()


    instructions = message.replace(bot_cmd, "")


"""
@tasks.loop(minutes=1)
async def check_schedule():

    if is_class_starting(class_days, start_hour):

        print("Class starting on", time.strftime("%d %b %y"))

        global invitation

        point_up = "☝️"
        invitation = "Hola, la ayudantía comenzará pronto."
        invitation += "Para asistir pica la manita y pasa a"
        invitation += class_channel.mention
        invitation += ". Tienes hasta las **10:30 AM** para ingresar"

        # invitation = await testing_channel.send(invitation)
        invitation = await announcements_channel.send(invitation)
        await invitation.add_reaction(point_up)

    if is_class_ending(class_days, end_hour):

        await class_channel.send("La ayundantía ha acabado")

        [await member.remove_roles(nerd_role) for member in members_list]
        await class_channel.purge(limit=None)
"""


@botzmann.event
async def on_ready():

    print("Logged on", time.strftime("%d %b %y"))

    global server
    server = botzmann.get_guild(server_id)

    global admin
    admin = await botzmann.fetch_user(admin_id)

    global members_list
    members_list = await server.fetch_members().flatten()

    global class_channel
    class_channel = botzmann.get_channel(class_channel_id)

    global announcements_channel
    announcements_channel = botzmann.get_channel(announcements_channel_id)

    global testing_channel
    testing_channel = botzmann.get_channel(testing_channel_id)

    global nerd_role
    nerd_role = discord.utils.get(server.roles, name="Nerd")

    [await member.remove_roles(nerd_role) for member in members_list]

    await check_schedule.start()


@botzmann.event
async def on_reaction_add(reaction, user):

    if (user != botzmann.user) and (invitation == reaction.message):

        print(user.display_name, "is here")
        await user.add_roles(nerd_role)


@botzmann.event
async def on_message(message):

    author_name = message.author.display_name
    origin = message.channel

    if message.author == botzmann.user:

        return

    elif message.content.startswith(tex_cmd):

        print("LaTeX render called")
        latex_render(message.content)
        if os.path.exists("reply.png"):

            await origin.send(
                "**" + author_name + "** dice:", file=discord.File("reply.png")
            )

            os.remove("reply.png")

        else:

            await origin.send(
                author_name + ", no pude compilar tu mensaje. Vúelvelo a intentar"
            )

    elif message.content.startswith(cts_cmd):

        print("Looking for contants with scipy")

        await origin.send(find_constant(message.content))

    elif message.content.startswith(ptn_cmd):

        await origin.send(pass_to_python(message.content))

    # TODO add a few more commands
    elif message.content.startswith("bot> purge!") and message.author == admin:

        await origin.purge(limit=None)

    else:

        pass


botzmann.run(token)
