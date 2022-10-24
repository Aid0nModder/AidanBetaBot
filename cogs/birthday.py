import discord
from discord.ext import commands, tasks, pages
from discord.commands import SlashCommandGroup
from discord import Option

import datetime

from functions import getComEmbed, dateToStr
from checks import command_checks_silent
from cooldowns import cooldown_etc

AC = discord.ApplicationContext
class BirthdayCog(discord.Cog):
	def __init__(self, client:commands.Bot):
		self.client = client

	async def ready(self):
		self.borths = await self.getBirthdays()
		self.daily_task.start()

	def cog_unload(self):
		self.daily_task.cancel()
	
	async def getBirthdays(self):
		borths = []
		now = "{dt.day}-{dt.month}".format(dt=datetime.datetime.now())
		for user in await self.client.UCON.loopdata():
			when = self.client.UCON.get_value(user, "birthday")
			if now == when:
				borths.append(user)
		return borths

	async def getUpcomingBirthdays(self, ctx:AC):
		birthlist = []
		for user in await self.client.UCON.loopdata():
			if user in ctx.guild.members:
				when = self.client.UCON.get_value(user, "birthday")
				if when:
					day, month = when.split("-")
					birthlist.append([user,int(day),int(month)])
		if len(birthlist) == 0:
			return await ctx.respond(f"No one in this server has set a birthday. You can change that by running /birthday set!")

		def sortfunc(e):
			return e[1]+(e[2]*31)
		birthlist.sort(key=sortfunc)

		today = str(datetime.date.today()).split("-")
		today = [int(e) for e in today]
		for i in range(1,len(birthlist)): # thanks for wasting my sweet time.
			# if birth month is higher than todays month or month is same and birth day is higher than todays day
			if birthlist[0][2] > today[1] or (birthlist[0][2] == today[1] and birthlist[0][1] > today[2]):
				break
			else:
				birthlist.append(birthlist.pop(0))

		return birthlist

	async def nextDay(self):
		if self.client.isbeta: return

		for user in self.borths: # no longer birthday :(
			for guild in self.client.guilds:
				if user in guild.members:
					if not await command_checks_silent(None, self.client, guild=guild, user=user, is_guild=True, bot_has_permission="manage_roles"):
						member = guild.get_member(user.id)

						role = self.client.CON.get_value(guild, "birthday_role", guild=guild)
						if role and role in member.roles:
							await member.remove_roles(role)

		self.borths = await self.getBirthdays()
		for user in self.borths: # is birthday :)
			for guild in self.client.guilds:
				if user in guild.members:
					member = guild.get_member(user.id)

					channel = self.client.CON.get_value(guild, "birthday_announcement_channel", guild=guild)
					msg = self.client.CON.get_value(guild, "birthday_announcement_message")
					if channel and msg:
						await channel.send(msg.format(name=user.name, mention=user.mention, user=user, member=user))
					
					if not await command_checks_silent(None, self.client, guild=guild, user=user, is_guild=True, bot_has_permission="manage_roles"):
						role = self.client.CON.get_value(guild, "birthday_role", guild=guild)
						if role:
							await member.add_roles(role)

	@tasks.loop(time=datetime.time(0, 0, 0, 0, datetime.datetime.now().astimezone().tzinfo))
	async def daily_task(self):
		await self.nextDay()

	###

	borthgroup = SlashCommandGroup("birthday", "Birthday commands.")

	@borthgroup.command(name="change", description="Set or remove your birthday. To remove leave day and month arguments blank")
	@commands.dynamic_cooldown(cooldown_etc, commands.BucketType.user)
	async def change(self, ctx:AC,
		day:Option(int, "Day of your birthday.", min_value=1, max_value=31, required=False),
		month:Option(int, "Month of your birthday.", min_value=1, max_value=12, required=False),
	):
		if (not day) and (not month):
			await self.client.UCON.set_value(ctx.author, "birthday", False)
			await ctx.respond("Remeoved your birthday from the database.")
		if (not (day and month)):
			await ctx.respond("Command requires both or neither argument.")
		else:
			if day >= 1 and (((month == 1 or month == 3 or month == 5 or month == 7 or month == 9 or month == 11) and day <= 31) or ((month == 4 or month == 6 or month == 8 or month == 10 or month == 12) and day <= 30) or (month == 2 and day <= 29)):
				await self.client.UCON.set_value(ctx.author, "birthday", f"{day}-{month}")
				await ctx.respond(f"Birthday set to the {dateToStr(day, month)}")
			else:
				await ctx.respond(f"Nice try but the {dateToStr(day, month)} isn't real, Enter a valid date please.")

	@borthgroup.command(name="upcoming", description="Upcoming birthdays.")
	@commands.dynamic_cooldown(cooldown_etc, commands.BucketType.user)
	async def upcoming(self, ctx:AC):	
		birthlist = await self.getUpcomingBirthdays(ctx)

		def getbirthdaylistembed(birthdays, first):
			fields = []
			for birth in birthdays:
				txt = dateToStr(birth[1], birth[2])
				fields.append([f"{birth[0]}:", txt])
			content = "Other Birthdays:"
			if first:
				content = "🎊🎊🎊 Upcoming Birthdays:"
			return getComEmbed(ctx, self.client, content, "Is your birthday coming soon? Use /birthday set to add yours!", fields=fields)

		def divide_chunks(l, n):
			for i in range(0, len(l), n):
				yield l[i:i + n]

		infopages = []
		first = True
		questionchunks = divide_chunks(birthlist, 5)
		for qc in questionchunks:
			infopages.append(getbirthdaylistembed(qc, first))
			if first: first = False

		infopagesbuttons = [
			pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.blurple),
			pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True),
			pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.blurple),
		]
		paginator = pages.Paginator(pages=infopages, loop_pages=True, disable_on_timeout=True, timeout=60, use_default_buttons=False, custom_buttons=infopagesbuttons)
		await paginator.respond(ctx.interaction)

def setup(client):
	client.add_cog(BirthdayCog(client))