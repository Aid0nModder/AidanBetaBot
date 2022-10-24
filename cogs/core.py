import asyncio
import discord
from discord.ext import commands, pages
from discord.commands import slash_command, SlashCommandGroup
from discord.utils import get
from discord import Option, Color, Embed, OptionChoice

from github.Issue import Issue

import time
from datetime import datetime

from bot import getCONnames, getUCONnames, getGithubtags
from config import ConfigManager
from functions import getComEmbed
from checks import command_checks, command_checks_silent, permission_check
from cooldowns import cooldown_core

CONvaluenames = getCONnames()
UCONvaluenames = getUCONnames()
GithubTags = getGithubtags()

AC = discord.ApplicationContext
def permissionStates(ctx:AC, client:commands.Bot):
	permissions = [
		"view_channel","manage_channels","manage_roles","manage_emojis_and_stickers","view_audit_log","view_guild_insights","manage_webhooks","manage_guild", "create_instant_invite",
		"change_nickname","manage_nicknames","kick_members","ban_members","moderate_members","send_messages","send_messages_in_threads","create_public_threads","create_private_threads",
		"embed_links","attach_files","add_reactions","external_emojis","external_stickers","mention_everyone","manage_messages","manage_threads","read_message_history",
		"send_tts_messages","use_application_commands","manage_events","administrator"
	]
	requiredperms = {
		"view_channel": "Needed to send messages for commands",
		"manage_webhooks": "Needed to send messages as users for things like /clone and nitron't*",
		"send_messages": "Needed to send messages for commands",
		"send_messages_in_threads": "Needed to send messages for commands in threads",
		"embed_links": "Needed to embed links in /echo and /issue*",
		"external_emojis": "Needed to send private emojis for several commands including /opinion and /games, as well as nitron't",
		"external_stickers": "Needed to send private stickers for nitron't",
		"manage_messages": "Needed to delete messages with invites if remove_invites is enabled",
		"read_message_history": "Needed to see past messages for /info"
	}
	optionalperms = {
		"manage_roles":"If disabled /role and birthday_role will no longer be avalable",
		"manage_guild":"If disabled guild invites wont be ignored if remove_invites is enabled",
		"mention_everyone":"If disabled qotd_role will not work",
		"attach_files":"If disabled /echo, /clone and nitron't will not have attachment support"
	}
	unnecessaryperms = [
		"manage_channels","manage_emojis_and_stickers","view_audit_log","view_guild_insights","create_instant_invite",
		"change_nickname","manage_nicknames","kick_members","ban_members","moderate_members","create_public_threads","create_private_threads",
		"add_reactions","manage_threads","send_tts_messages","use_application_commands","manage_events","administrator"
	]
	clientmember = get(ctx.guild.members, id=client.user.id)

	rtxt = ""
	for perm in requiredperms:
		if not permission_check(clientmember, ctx.channel, perm):
			rtxt += "`" + perm + " - " + requiredperms[perm] + "`\n"
	if rtxt == "":
		rtxt = f"Hoo ray! You have given {client.name} all the neccacary permissions!"
		
	otxt = ""
	for perm in optionalperms:
		if not permission_check(clientmember, ctx.channel, perm):
			otxt += "`" + perm + " - " + optionalperms[perm] + "`\n"
	if otxt == "":
		otxt = f"What a CHAD! You have given {client.name} all the optional permissions!"

	utxt = ""
	for perm in unnecessaryperms:
		if permission_check(clientmember, ctx.channel, perm):
			utxt += "`" + perm + " - Not needed in this current version`\n"
	if utxt == "":
		utxt = f"Smart Admin! You have not given {client.name} any unnecessary permissions!"

	return [["Required",rtxt],["Optional",otxt],["Unnecessary",utxt]]

# man, what a throwback
class CoreCog(discord.Cog):
	def __init__(self, client:commands.Bot):
		self.client = client

	@slash_command(name="info", description="Get info about the bot.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def info(self, ctx:AC):
		infopages = [
			getComEmbed(ctx, self.client, "Info > General", f'''
				{self.client.info}

				[Aidan's Youtube](https://www.youtube.com/c/AidanMapper)
				[Aidan's Discord Server](https://discord.gg/KXrDUZfBpq)
				[{self.client.name}'s Privacy Policy](https://github.com/Aid0nModder/AidanBot#privacy-policy)
				[{self.client.name}'s Terms of Service](https://github.com/Aid0nModder/AidanBot#terms-of-service)

				**Guild Status:** `{self.client.CON.get_value(ctx.guild, "guild_status")}`
			'''),
			getComEmbed(ctx, self.client, "Info > Permissions", "```(options marked with a * may become optional in the future)\n\n- Required: must be enabled as it can cause serious issues to both user and bot.\n- Optional: can be enabled or disabled without major disturbance, though some functionality can be lost.\n- Unnecessary: aren't required yet and should be disabled to keep safe.\n\n(Permissions not mentioned are fine as is, enabled or not.)```", fields=permissionStates(ctx, self.client)),
		]
		infopagesbuttons = [
			pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.blurple),
			pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True),
			pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.blurple),
		]
		paginator = pages.Paginator(pages=infopages, loop_pages=True, disable_on_timeout=True, timeout=60, use_default_buttons=False, custom_buttons=infopagesbuttons)
		await paginator.respond(ctx.interaction)

	@slash_command(name="ping", description="Check the Bot and API latency.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def ping(self, ctx:AC):
		start_time = time.time()
		await ctx.respond("Testing Ping...", ephemeral=True)
		apitime = time.time() - start_time
		await ctx.edit(content="Ping Pong motherfliper!```\nBOT: {:.2f} seconds\nAPI: {:.2f} seconds\n```".format(self.client.latency, apitime))
		
	@slash_command(name="echo", description="Say something as me.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def echo(self, ctx:AC,
		message:Option(str, "What I will say.", required=True),
		attachment:Option(discord.Attachment, "What attachment will he attach.", required=False)
	):
		if attachment and (not await command_checks_silent(ctx, self.client, is_guild=True, bot_has_permission="attach_files")):
			files = await self.client.attachmentsToFiles([attachment])
		else:
			files = []
		await ctx.send(message, files=files)
		await ctx.respond("Sent!", ephemeral=True)

	@slash_command(name="embed", description="Send a custom embed.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def embed(self, ctx:AC,
		title:Option(str, "Title of the embed.", required=True),
		description:Option(str, "Description of the embed.", required=True),
		color:Option(str, "Color of the embed", choices=[
			OptionChoice(name="system gray", value="sys-gray"),
			OptionChoice(name="system red", value="sys-red"),
			OptionChoice(name="system dark red", value="sys-darkred"),
			OptionChoice(name="red", value="red"),
			OptionChoice(name="green", value="green"),
			OptionChoice(name="blue", value="blue"),
			OptionChoice(name="gold", value="gold"),
			OptionChoice(name="gray", value="gray"),
		], required=True),
		timestamp:Option(bool, "if timestamp is enabled.", required=False, default=False),
		header:Option(str, "Header of the embed.", required=False, default=""),
		headerimg:Option(str, "Image (Link) next to the header of the embed.", required=False, default=False),
		footer:Option(str, "Footer of the embed.", required=False, default=""),
		footerimg:Option(str, "Image (Link) next to the header of the embed.", required=False, default=False),
		image:Option(str, "Image (Link) That will appear at the bottom of the embed.", required=False, default=False),
		thumbnail:Option(str, "Image (Link) That will appear on the right side of the embed.", required=False, default=False),
		field1:Option(str, "A field of the emebd, split title and value with '|'", required=False, default=False),
		field2:Option(str, "A field of the emebd, split title and value with '|'", required=False, default=False),
		field3:Option(str, "A field of the emebd, split title and value with '|'", required=False, default=False)
	):
		if color == "sys-gray": color = Color.from_rgb(20, 29, 37)
		if color == "sys-red": color = Color.from_rgb(220, 29, 37)
		if color == "sys-darkred": color = Color.from_rgb(120, 29, 37)
		if color == "red": color = Color.from_rgb(225, 15, 15)
		if color == "green": color = Color.from_rgb(15, 225, 15)
		if color == "blue": color = Color.from_rgb(15, 15, 225)
		if color == "gold": color = Color.from_rgb(225, 120, 15)
		if color == "gray": color = Color.from_rgb(165, 165, 165)
		if timestamp: timestamp = datetime.now()

		emb = Embed(title=title, description=description, color=color, timestamp=timestamp)
		if footer != "" or footerimg:
			emb.set_footer(text=footer, icon_url=footerimg)
		if header != "" or headerimg:
			emb.set_author(name=header, icon_url=headerimg)
		if image:
			emb.set_image(url=image)
		if thumbnail:
			emb.set_thumbnail(url=thumbnail)

		if field1:
			field1 = field1.split("|")
			if len(field1) > 2 and field1[2] == "true":
				emb.add_field(name=field1[0], value=field1[1], inline=True)
			else:
				emb.add_field(name=field1[0], value=field1[1], inline=False)
		if field2:
			field2 = field2.split("|")
			if len(field2) > 2 and field2[2] == "true":
				emb.add_field(name=field2[0], value=field2[1], inline=True)
			else:
				emb.add_field(name=field2[0], value=field2[1], inline=False)
		if field3:
			field3 = field3.split("|")
			if len(field3) > 2 and field3[2] == "true":
				emb.add_field(name=field3[0], value=field3[1], inline=True)
			else:
				emb.add_field(name=field3[0], value=field3[1], inline=False)

		await ctx.send(embed=emb)
		await ctx.respond("Sent!", ephemeral=True)

	@slash_command(name="clone", description="Say something as another user.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def clone(self, ctx:AC,
		user:Option(discord.Member, "Member you want to clone.", required=True),
		message:Option(str, "Message you want to make them send.", required=True),
		attachment:Option(discord.Attachment, "What you want to attach.", required=False),
	):
		if attachment and (not await command_checks_silent(ctx, self.client, is_guild=True, bot_has_permission="attach_files")):
			files = await self.client.attachmentsToFiles([attachment])
		else:
			files = []

		if self.client.UCON.get_value(user, "clone_disabled", guild=ctx.guild):
			await ctx.respond("This user has disabled cloning, try a different user!", ephemeral=True)
		else:
			await ctx.defer(ephemeral=True)
			await self.client.sendWebhook(ctx.channel, user, message, files, f" (Cloned by {str(ctx.author)})")
			await ctx.respond("Sent!", ephemeral=True)

	@slash_command(name="issue", description="Create an issue on GitHub.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def issue(self, ctx:AC,
		title:Option(str, "Title of the post.", required=True),
		body:Option(str, "Body of the post.", required=True),
		label1:Option(str, "1st Tag for the post.", choices=GithubTags, required=False),
		label2:Option(str, "2nd Tag for the post.", choices=GithubTags, required=False),
		label3:Option(str, "3rd Tag for the post.", choices=GithubTags, required=False)
	):
		body += f"\n\n[ Submitted by {str(ctx.author)} via /issue ]"
		labels = [i for i in [label1, label2, label3] if i]
		if len(labels) > 0:
			issue:Issue = self.client.botrepo.create_issue(title=title, body=body, labels=labels)
		else:
			issue:Issue = self.client.botrepo.create_issue(title=title, body=body)
		await ctx.respond(f"Submitted!\n\n{issue.html_url}")

	@slash_command(name="role", description="Add a role to you or someone. Can only add [r] roles to yourself without manage_roles.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def role(self, ctx:AC,
		role:Option(discord.Role, "Role to add/remove to yourself.", required=True),
		user:Option(discord.Member, "User to add/remove the role to.", required=False),
		action:Option(str, "If you want to add or remove a role.", choices=["add","remove"], default="add"),
	):
		if await command_checks(ctx, self.client, is_guild=True, bot_has_permission="manage_roles"): return
		if ((user and user != ctx.author) or (not role.name.startswith("[r]"))) and (not ctx.channel.permissions_for(ctx.author).manage_roles):
			return await ctx.respond("HAHA, Maybe one day kiddo...")
		clientmember = get(ctx.guild.members, id=self.client.user.id)
		if role.position >= clientmember.top_role.position:
			return await ctx.respond("Sorry, can't give roles above my top role.")
		if role.position >= ctx.author.top_role.position:
			return await ctx.respond("Sorry, can't give roles above your top role.")
		user = user or ctx.author
		if action == "add":
			await user.add_roles(role)
			await ctx.respond(f"Added {role.mention} to {user.mention}!")
		else:
			await user.remove_roles(role)
			await ctx.respond(f"Removed {role.mention} from {user.mention}!")

	# CONFIG #

	configgroup = SlashCommandGroup("config", "Config commands.")
	
	@configgroup.command(name="guild", description="Guild configerations.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def guildconfig(self, ctx:AC,
		action:Option(str, "Config action.", choices=["List","Set","Reset","Info","Getraw"], required=True),
		name:Option(str, "Variable you're performing action on.", choices=CONvaluenames, required=False),
		value:Option(str, "New value for this Variable.", required=False),
	):
		if await command_checks(ctx, self.client, is_guild=True, has_mod_role=True): return
		await self.config_command(ctx, self.client.CON, ctx.guild, action, name, value)

	@configgroup.command(name="user", description="User configerations.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def userconfig(self, ctx:AC,
		action:Option(str, "Config action.", choices=["List","Set","Reset","Info","Getraw"], required=True),
		name:Option(str, "Variable you're performing action on. Required for all but 'List'.", choices=UCONvaluenames, required=False),
		value:Option(str, "New value for this Variable. Required for 'Set'.", required=False)
	):
		await self.config_command(ctx, self.client.UCON, ctx.author, action, name, value)
	
	async def config_command(self, ctx, CON, obj, action="List", name=None, value=None):
		values = CON.get_group(obj)
		embed = False
		if action == "List":
			txt = ""
			for name in values:
				if CON.is_restricted(name) != True:
					txt += f"\n**- {name}:** {CON.display_value(name, CON.get_value(obj, name, ctx.guild))}"
			embed = getComEmbed(ctx, self.client, f"All values for {obj.name}:", txt)
		elif action == "Info" and name:
			txt = f"**Value:** {CON.display_value(name, values[name])}\n**Default Value:** `{CON.default_values[name]}`\n**Description:** '{CON.desc_values[name]}'\n**Type:** `{CON.type_values[name]}`\n**Stackable:** `{CON.stackable_values[name]}`"
			embed = getComEmbed(ctx, self.client, f"Info for {name}:", txt)
		elif action == "Getraw" and name:
			txt = f"```{CON.raw_value(name, values[name])}```"
			embed = getComEmbed(ctx, self.client, f"Raw of {name}:", txt)
		elif action == "Reset" and name:
			await CON.reset_value(obj, name)
			embed = getComEmbed(ctx, self.client, content=f"Reset {name} to `{CON.default_values[name]}`!")
		elif action == "Set" and name and value:
			fulval, error = await CON.set_value(obj, name, value, ctx.guild)
			if error:
				embed = getComEmbed(ctx, self.client, content=error)
			else:
				embed = getComEmbed(ctx, self.client, content=f"Set {name} to {CON.display_value(name, CON.get_value(obj, name, ctx.guild))}!")
		else:
			return await ctx.respond("Seems like you're missing some arguments. Try again.")
		await ctx.respond(embed=embed)

	###

	'''async def config_command(self, ctx:AC, CON:ConfigManager, obj:discord.Guild|discord.Member):
		values = CON.get_group(obj)
		valid = []
		for name in values:
			if CON.is_restricted(name) != True:
				valid.append(name)

		confpage = 0
		confpages = {}
		confoptions = []
		for name in valid:
			confpages[name] = getComEmbed(ctx, self.client, f"Guild Config > {name}", "Still a WIP command. Info will be here in the future!")
			confoptions.append(discord.SelectOption(label=name, value=name, description=CON.desc_values[name]))

		emb, view = confpages[confpage], discord.ui.View(
			discord.ui.Select(placeholder="Select Value", custom_id="select", options=confoptions),
			discord.ui.Button(label="Change", style=discord.ButtonStyle.green, custom_id="change", row=1),
			discord.ui.Button(label="Reset", style=discord.ButtonStyle.red, custom_id="reset", row=1),
		)
		response = await ctx.respond(embed=emb,view=view)
		msg = await response.original_message()

		def check(interaction:discord.Interaction):
			return (interaction.user.id == ctx.author.id and interaction.message.id == msg.id)

		while True:
			try:
				interaction = await self.client.wait_for("interaction", check=check, timeout=180)
				await interaction.response.defer()
				id = interaction.custom_id
				print(id)
			except asyncio.TimeoutError:
				await ctx.edit("Timeout")

	@configgroup.command(name="guild-new", description="Guild configerations.")
	@commands.dynamic_cooldown(cooldown_core, commands.BucketType.user)
	async def guildconfignew(self, ctx:AC):
		if await command_checks(ctx, self.client, is_guild=True, has_mod_role=True): return
		await self.newconfig_command(ctx, self.client.CON, ctx.guild)'''

def setup(client):
	client.add_cog(CoreCog(client))