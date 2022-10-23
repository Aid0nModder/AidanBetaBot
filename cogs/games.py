import discord
import discord.ext.commands as CM
import discord.app_commands as AC
from discord import Interaction as Itr

import asyncio
from random import choice
from typing import Literal

from aidanbot import AidanBot
from cooldowns import cooldown_games
from functions import getComEmbed, userPostedRecently

rps_options = ["rock", "paper", "scissors"]
rps_optionsemoji = {"rock":"👊", "paper":"✋", "scissors":"✌️"}

from cogs.fightmodes.fight_normal import FMN as N_FMN
from cogs.fightmodes.fight_normal import FP as N_FP
from cogs.fightmodes.fight_classic import FMN as C_FMN
from cogs.fightmodes.fight_classic import FP as C_FP

class GamesCog(CM.Cog):
	def __init__(self, client:AidanBot):
		self.client = client

	async def canPlay(self, itr:Itr, user:discord.Member):
		# not a bot and dnd enabled and no messages in last 5 messages.
		if (not user.bot) and self.client.UCON.get_value(user, "games_disabled", guild=itr.guild) and (not await userPostedRecently(itr.channel, user, 5)):
			await itr.response.send_message("This user has DND enabled and hasn't spoken recently (In this channel), this game can not be started, ask them to join you first.", ephemeral=True)
			return False
		return True

	async def defaultUsers(self, itr:Itr, user1:discord.Member=None, user2:discord.Member=None):
		if user1 and user2:
			return user1, user2
		elif user1:
			return user1, itr.user
		elif user2:
			return itr.user, user2
		else:
			return itr.user, await itr.guild.fetch_member(itr.client.user.id)

	###

	class rpsPlayer():
		def __init__(self, user:discord.Member):
			self.id = user.id
			self.name = user.display_name
			self.bot = user.bot
			if self.bot:
				self.pick = choice(rps_options)
			else:
				self.pick = ""
			
		@property
		def getEmoji(self):
			return rps_optionsemoji[self.pick]
			
	gamesgroup = AC.Group(name="games", description="Commands to do with games.")

	@gamesgroup.command(name="rps", description="Rock, paper, scissors!")
	@AC.describe(user1="The first player.", user2="The second player.")
	@CM.dynamic_cooldown(cooldown_games, CM.BucketType.guild)
	async def rps(self, itr:Itr, user1:discord.Member=None, user2:discord.Member=None):
		user1, user2 = await self.defaultUsers(itr, user1, user2)
		if not ((itr.user == user1 or await self.canPlay(itr, user1)) and (itr.user == user2 or await self.canPlay(itr, user2))):
			return
		player1, player2 = self.rpsPlayer(user1), self.rpsPlayer(user2)

		def getRPSEmbed(timeout=None, finish=None):
			embed = ""
			if finish:
				embed = getComEmbed(str(itr.user), self.client, finish, f"{player1.name}: `{player1.getEmoji}`   |   {player2.name}: `{player2.getEmoji}`")
			else:
				embed = getComEmbed(str(itr.user), self.client, "Choose your choice.", f"{player1.name}: `?`   |   {player2.name}: `?`")

			if (player1.bot and player2.bot):
				timeout = True
			view = discord.ui.View(timeout=None)
			view.add_item(discord.ui.Button(label="rock", style=discord.ButtonStyle.green, custom_id="rock", emoji="👊", disabled=timeout))
			view.add_item(discord.ui.Button(label="paper", style=discord.ButtonStyle.green, custom_id="paper", emoji="✋", disabled=timeout))
			view.add_item(discord.ui.Button(label="scissors", style=discord.ButtonStyle.green, custom_id="scissors", emoji="✌️", disabled=timeout))
			return embed, view

		embed, view = getRPSEmbed()
		await itr.response.send_message(embed=embed, view=view)
		
		def check(checkitr:Itr):
			return (((checkitr.user.id == player1.id and player1.pick == "") or (checkitr.user.id == player2.id and player2.pick == "")))

		if (player1.bot and player2.bot):
			await asyncio.sleep(1.5)
		else:
			while True:
				try:
					butitr:Itr = await self.client.wait_for("interaction", timeout=30, check=check)
					if butitr.user.id == player1.id:
						player1.pick = butitr.data["custom_id"]
						await butitr.response.send_message(f"Pick set to {player1.getEmoji}!", ephemeral=True)
					else:
						player2.pick = butitr.data["custom_id"]
						await butitr.response.send_message(f"Pick set to {player2.getEmoji}!", ephemeral=True)
					if player1.pick != "" and player2.pick != "":
						break
				except asyncio.TimeoutError:
					embed, view = getRPSEmbed(True)
					await itr.edit_original_response(embed=embed, view=view)

		state = "Something broke lol, i'm gonna blame you. <:AidanSmug:837001740947161168>"
		if player1.pick == player2.pick:
			state = "Same result, draw."
		elif player1.pick == "paper" and player2.pick == "rock":
			state = f"Paper covers Rock, {player1.name} wins!"
		elif player1.pick == "rock" and player2.pick == "scissors":
			state = f"Rock breaks Scissors, {player1.name} wins!"
		elif player1.pick == "scissors" and player2.pick == "paper":
			state = f"Scissors cuts Paper, {player1.name} wins!"
		elif player1.pick == "rock" and player2.pick == "paper":
			state = f"Paper covers Rock, {player2.name} wins!"
		elif player1.pick == "scissors" and player2.pick == "rock":
			state = f"Rock breaks Scissors, {player2.name} wins!"
		elif player1.pick == "paper" and player2.pick == "scissors":
			state = f"Scissors cuts Paper, {player2.name} wins!"

		embed, view = getRPSEmbed(True, state)
		await itr.edit_original_response(embed=embed, view=view)

	###

	async def fight(self, itr:Itr, mode:str=None, user1:discord.Member=None, user2:discord.Member=None, ailevel:str=None, ailevel1:str=None, ailevel2:str=None):
		core, turn, turnt = "", "", ""
		if mode == "normal":
			core = N_FMN(user1, user2, ailevel, ailevel1, ailevel2)
			turn:N_FP = core.turn
			turnt:N_FP = core.turnt
		elif mode == "classic":
			core = C_FMN(user1, user2, ailevel, ailevel1, ailevel2)
			turn:C_FP = core.turn
			turnt:C_FP = core.turnt
			
		embed, view = core.getEmbed(itr, self.client, turn)
		await itr.response.send_message(embed=embed, view=view)
		MSG = await itr.original_response()

		def check(checkitr:Itr):
			return (checkitr.message.id == MSG.id and checkitr.user.id == turn.id)
		while True:
			try:
				move = ""
				if turn.special:
					move = turn.special
					await asyncio.sleep(2.5)
				elif turn.bot:
					move = turn.makeMove()
					await asyncio.sleep(2.5)
				else:
					butitr:Itr = await self.client.wait_for("interaction", check=check, timeout=180)
					await butitr.response.defer()
					move = butitr.data["custom_id"]

				end, endid = False, ""
				if move == "flee":
					end, endid = True, "flee"
				else:
					end, endid = core.useMove(move)
				if end:
					if endid.endswith("-killself") or endid == "flee":
						turn, turnt = core.swapTurn()
					embed, view = core.getWinEmbed(itr, self.client, endid, turn, turnt)
					await itr.edit_original_response(embed=embed, view=view)
					return

				turn, turnt = core.swapTurn()
				embed, view = core.getEmbed(itr, self.client, turn)
				await itr.edit_original_response(embed=embed, view=view)

			except asyncio.TimeoutError:
				embed, view = core.getEmbed(itr, self.client, turn, True)
				await itr.edit_original_response(embed=embed, view=view)
				return

	@gamesgroup.command(name="fight", description="Fight against another user or one of the main AI levels.")
	@AC.describe(user1="The first player.", user2="The second player.", ailevel="AI level for the bot.",
		ailevel1="AI level for player 1 if a bot, overrides master.", ailevel2="AI level for player 2 if a bot, overrides master."
	)
	@CM.dynamic_cooldown(cooldown_games, CM.BucketType.guild)
	async def fight_normal(self, itr:Itr, user1:discord.Member=None, user2:discord.Member=None,
		ailevel:Literal["dead","random","easy","medium","hard"]="medium", ailevel1:Literal["dead","random","easy","medium","hard"]=None, ailevel2:Literal["dead","random","easy","medium","hard"]=None
	):
		user1, user2 = await self.defaultUsers(itr, user1, user2)
		if not ((itr.user == user1 or await self.canPlay(itr, user1)) and (itr.user == user2 or await self.canPlay(itr, user2))):
			return
		await self.fight(itr, "normal", user1, user2, ailevel, ailevel1, ailevel2)

	@gamesgroup.command(name="fight-classic", description="Fight against another user or one of the main AI levels. Full recreation of the original fight.")
	@AC.describe(user1="The first player.", user2="The second player.", ailevel="AI level for the bot.",
		ailevel1="AI level for player 1 if a bot, overrides master.", ailevel2="AI level for player 2 if a bot, overrides master."
	)
	@CM.dynamic_cooldown(cooldown_games, CM.BucketType.guild)
	async def fight_classic(self, itr:Itr, user1:discord.Member=None, user2:discord.Member=None,
		ailevel:Literal["dead","random","easy","hard"]="easy", ailevel1:Literal["dead","random","easy","hard"]=None, ailevel2:Literal["dead","random","easy","hard"]=None
	):
		user1, user2 = await self.defaultUsers(itr, user1, user2)
		if not ((itr.user == user1 or await self.canPlay(itr, user1)) and (itr.user == user2 or await self.canPlay(itr, user2))):
			return
		await self.fight(itr, "classic", user1, user2, ailevel, ailevel1, ailevel2)

async def setup(client:AidanBot):
	await client.add_cog(GamesCog(client), guilds=client.debug_guilds)