import discord
from discord import ButtonStyle as Style
from discord import Interaction as Itr

import math
from random import randint, choice

from aidanbot import AidanBot
from functions import getBar, getComEmbed

# Fight_Player
class FP():
	def __init__(self, user:discord.Member, id:str, ai:str):
		self.user = user
		self.playerid = id
		self.enemy:FP = False
		self.ailevel = ai

		self.health = 100
		self.energy = 4
		self.heals = 2

	@property
	def name(self):
		if self.enemy.user == self.user:
			return self.user.display_name+f" [{self.playerid}]"
		else:
			return self.user.display_name
	@property
	def id(self):
		return self.user.id
	@property
	def bot(self):
		return self.user.bot

	@property
	def disable(self):
		return False
	@property
	def special(self):
		return False

	@property
	def ui(self):
		return [f"{self.name} Stats:", f'''
		`Health :` {getBar(self.health,100,10,True)} **({self.health}) (🍷 x{self.heals})**
		`Energy :` {getBar(self.energy,10,5,True,'red')}  **({self.energy})**
		''']

	def clamp(self):
		self.health, self.energy = clamp(self.health,0,100), clamp(self.energy,0,10)

	def getDamage(self):
		return (self.energy*4)+5

	## AI ##

	def makeMove(self):
		if self.ailevel == "dead": return "wait"
		if self.ailevel == "random": return self.makeMoveRandom()
		if self.ailevel == "easy": return self.makeMoveEasy()
		if self.ailevel == "hard": return self.makeMoveHard()

	def makeMoveEasy(self):
		if self.heals > 0 and self.health <= 50 and max(1,randint(1, math.floor(self.health/10)) == 1): return "heal"
		if self.energy >= 7 and randint(self.energy,10) == 10: return "punch"
		if self.energy >= 4 and randint(1,3) == 1: return "slap"
		return "wait"
	def makeMoveHard(self):
		if self.heals > 0 and self.health <= self.enemy.getDamage(): return "heal"
		if self.energy == 10 or self.getDamage() >= self.enemy.health: return "punch"
		if self.energy == 9: return "slap"
		return "wait"
	def makeMoveRandom(self):
		opt = ["wait","slap"]
		if self.energy > 0: opt.append("punch")
		if self.heals > 0: opt.append("heal")
		return choice(opt)

# Fight_Manager
class FMN():
	def __init__(self, user1:discord.Member, user2:discord.Member, ai:str, ai1:str, ai2:str):
		ai1, ai2 = ai1 or ai, ai2 or ai
		self.player1, self.player2 = FP(user1,"1",ai1), FP(user2,"2",ai2)
		self.player1.enemy, self.player2.enemy = self.player2, self.player1
		self.moves = FM(self)
		self.turnid = 1
		self.actions = None

	## DO NOT TOUCH \/ ##
	
	@property
	def turn(self):
		if self.turnid == 1:
			return self.player1
		return self.player2
	@property
	def turnt(self):
		if self.turnid == 1:
			return self.player2
		return self.player1

	def swapTurn(self):
		self.turnid = 1 if self.turnid == 2 else 2
		return self.turn, self.turnt
	
	def getEmbed(self, itr:Itr, client:AidanBot, turn:FP, timeout=False):
		title = f"{self.player1.name} VS {self.player2.name}"
		fields = [self.player1.ui, self.player2.ui]
		if self.actions:
			fields.append(self.actions)
		if not timeout:
			fields.append([f"{turn.name}'s Turn:", "> Select an action below"])
		return getComEmbed(str(itr.user), client, title, fields=fields), self.moves.getView(timeout)
	def getWinEmbed(self, itr:Itr, client:AidanBot, move:str, turn:FP, turnt:FP):
		return getComEmbed(str(itr.user), client, f"{turn.name} won! Tough luck {turnt.name}", self.moves.getDeath(move).format(turn=turn.name, turnt=turnt.name)), self.moves.getView(True)

	def _getActions(self, changes, move):
		ap = self.getActions(move)
		if ap: actions = ap
		else: actions = [f"{self.turn.name} used {move}!"]
		if len(changes) > 0:
			txt = ""
			for change in changes:
				target = self.turn if change[0] == "turn" else self.turnt
				match change[1]:
					case "health-": txt += f"> {target.name} Lost **{change[2]} Health**.\n"
					case "health+": txt += f"> {target.name} Gained **{change[2]} Health**.\n"
					case "energy-": txt += f"> {target.name} Lost **{change[2]} Energy**.\n"
					case "energy+": txt += f"> {target.name} Gained **{change[2]} Energy**.\n"
					case "mp-": txt += f"> {target.name} Lost **{change[2]} MP**.\n"
					case "mp+": txt += f"> {target.name} Gained **{change[2]} MP**.\n"
					case "multipliers": txt += f"> {target.name}'s Multipliers set to **x{target.multiplier}**.\n"
			actions.append(txt)
		else:
			actions.append("Nothing changed.")
		self.actions = actions

	def useMove(self, move):
		changes = self.moves.useMove(move)
		changes = self.doUpdate(move, changes, self.turn, self.turnt)
		self.turn.clamp(); self.turnt.clamp()
		self._getActions(changes, move)
		if self.turnt.health <= 0:
			return True, move
		elif self.turn.health <= 0:
			return True, move+"-killself"
		else:
			return False, False

	## DO NOT TOUCH /\ ##

	def getActions(self, move):
		if move == "heal" and self.turn.heals == 0:
			return [f"{self.turn.name} used {move}! That was their last..."]
		return False

	def doUpdate(self, move, changes:list, turn:FP, turnt:FP):
		if move != "punch":
			if move == "slap":
				turn.energy += 1
				changes.append(["turn","energy+",1])
			else:
				turn.energy += 2
				changes.append(["turn","energy+",2])
		return changes

# Fight_Moves
class FM():
	def __init__(self, core:FMN):
		self.core = core
	def getDeath(self, move):
		return self.deathmessages[move]
	def useMove(self, move):
		movefunc = getattr(self, move)
		return movefunc(self.core.turn, self.core.turnt)

	deathmessages = {
		"punch": "{turn} punched {turnt} into oblivion.",
		"slap": "{turnt} was slapped silly by {turn}.",
		"flee": "{turnt} fled like a baby!"
	}

	def getView(self, timeout=False):
		turn = self.core.turn
		timeout = True if timeout or turn.disable or turn.bot else False
		cure, curh = turn.energy, turn.heals
		lowe, noh = (cure < 2), (curh == 0)

		view = discord.ui.View(timeout=None)
		view.add_item(discord.ui.Button( style=Style.red,   label=f"Punch [{max(cure,1)}]", custom_id="punch", row=0, disabled=(timeout or lowe), emoji="👊"))
		view.add_item(discord.ui.Button( style=Style.red,   label=f"Slap",                  custom_id="slap",  row=0, disabled=timeout,           emoji="🖐️"))
		view.add_item(discord.ui.Button( style=Style.green, label=f"Heal [x{curh}]",        custom_id="heal",  row=0, disabled=(timeout or noh),  emoji="🍷"))
		view.add_item(discord.ui.Button( style=Style.gray,  label=f"Wait",                  custom_id="wait",  row=0, disabled=timeout,           emoji="🕐"))
		view.add_item(discord.ui.Button( style=Style.gray,  label=f"Flee",                  custom_id="flee",  row=0, disabled=timeout,           emoji="✖️"))
		return view

	def wait(self, turn:FP, turnt:FP):
		return []

	def punch(self, turn:FP, turnt:FP):
		damage, energyloss = randint((turn.energy*4)-5, (turn.energy*4)+5), math.floor(turn.energy/2)
		turnt.health, turn.energy = turnt.health-damage, turn.energy-energyloss
		return [["turnt","health-",damage],["turn","energy-",energyloss]]
	def slap(self, turn:FP, turnt:FP):
		damage = randint(5,10)
		turnt.health -= damage
		return [["turnt","health-",damage]]
	def heal(self, turn:FP, turnt:FP):
		turn.health, turn.heals = turn.health+50, turn.heals-1 
		return [["turn","health+",50]]
		
def clamp(n, minn, maxn):
	return max(min(maxn, n), minn)