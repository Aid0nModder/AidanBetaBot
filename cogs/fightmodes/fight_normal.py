import discord
from discord import ButtonStyle as Style
from discord import Interaction as Itr

import math
from random import randint, choice

from aidanbot import AidanBot
from functions import getBar, getComEmbed

punch_damage = [8,18,30]
combo_damage_1 = [0,8,18]
combo_damage_2 = [0,18,30]
heal_gain = [5,10,25]

# Fight_Player
class FP():
	def __init__(self, user:discord.Member, id:str, ai:str):
		self.user = user
		self.playerid = id
		self.enemy:FP = False
		self.ailevel = ai

		self.health = 100
		self.energy = 3
		self.mp = 3
		self.multiplier = 1

		self.defaultmultiplier = 1
		self.comboing = False
		self.defending = False

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
		return self.comboing
	@property
	def special(self):
		return "comboend" if self.comboing else False

	@property
	def ui(self):
		return [f"{self.name} Stats:", f'''
		`Health    :` {getBar(self.health,100,10,True)} **({self.health})**
		`Energy/MP :` {getBar(self.energy,3,3,False,'red')} / {getBar(self.mp,3,3,False,'red')}
		`Multiplier:` **x{self.multiplier:.1f}**
		''']

	def clamp(self):
		self.health, self.energy, self.mp = clamp(self.health,0,100), clamp(self.energy,0,3), clamp(self.mp,0,3)

	def getDamage(self, value, multi=None):
		multi = multi if multi else self.multiplier
		dmg = value * multi
		if self.enemy.defending: dmg /= 2 # defending supersedes multiplier
		return math.floor(dmg)

	def getDamageAt(self, values, multi=None): # simulates what damage will be given with punch/combo
		return self.getDamage(values[self.energy-1], multi)

	## AI ##

	def makeMove(self):
		if self.comboing: return "-"
		if self.ailevel == "dead": return "wait"
		if self.ailevel == "random": return self.makeMoveRandom()
		if self.ailevel == "easy": return self.makeMoveEasy()
		if self.ailevel == "medium": return self.makeMoveMedium()
		if self.ailevel == "hard": return self.makeMoveHard()
		
	def makeMoveEasy(self): # oldfights ai but made for newfight
		if self.mp > 0 and self.health <= self.energy*25 and randint(0,3) < self.energy: return "heal"
		elif self.energy == 3 or (self.energy == 2 and randint(1,2) == 2) or (self.energy == 1 and randint(1,3) == 3): return "punch"
		else: return "wait"
	def makeMoveMedium(self): # like easy but understands new moves
		if self.energy > 0:
			if self.enemy.multiplier >= 2 and randint(1,4) != 4: return "defend"  # 75%
			if self.enemy.defending and randint(1,3) != 3: return "punch" # 66.6%
			if self.energy == 2 and self.health > 50 and randint(1,2) == 2: return "combo" # 50%
			if self.energy == 3 or randint(1,3) == 3: return "punch" # 33.3%
		if self.mp > 0:
			if self.mp == 3 and self.enemy.health <= 50: return "kamikaze"
			if self.mp == 2 and (self.enemy.defending or self.enemy.mp > 1) and randint(1,2) == 2: return "pierce" # 50%
			if self.mp == 1 and (self.health >= 40 or randint(1,3) == 3): return "attackup" # 33.3%
			if self.health <= self.energy*25 and randint(0,3) < self.energy: return "heal"
		return "wait"
	def makeMoveHard(self): # doesn't take any chances
		enemyhd, ushd, ushdplus = self.enemy.getDamageAt(punch_damage), self.getDamageAt(punch_damage), self.getDamageAt(punch_damage,self.multiplier+0.5)
		if enemyhd >= self.health:
			if (self.mp == 3 or (self.energy == 0 and self.mp > 0)) and randint(1,2) == 2: return "heal" # 50%
			if self.energy > 0: return "defend"
		if self.energy > 0:
			if self.energy > 1 and self.enemy.health <= self.getDamageAt(combo_damage_1)+self.getDamageAt(combo_damage_2,1): return "combo"
			if self.enemy.health <= self.getDamageAt(punch_damage) or self.energy == 3: return "punch"
		if self.energy > 0 and (not self.enemy.comboing) and self.enemy.energy == 0: return "defend"
		if self.mp == 3 and self.enemy.health <= 50: return "kamikaze"
		if self.mp == 2 and (15 > ushd or (self.enemy.mp > 1 and 10 > ushd)): return "pierce"
		if self.mp == 1 and ushdplus >= self.enemy.health: return "attackup"
		return "wait"
	def makeMoveRandom(self):
		opt = ["wait"]
		if self.energy > 0: opt.append("punch"); opt.append("defend")
		if self.energy > 1: opt.append("combo")
		if self.mp == 1: opt.append("attackup")
		if self.mp == 2: opt.append("pierce")
		if self.mp == 3: opt.append("kamikaze")
		if self.mp > 0: opt.append("heal")
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
		if move == "comboend":
			return [f"{self.turn.name} finished combo!"]
		return False

	def doUpdate(self, move, changes:list, turn:FP, turnt:FP):
		if move == "punch" or move == "combo":
			if turn.multiplier > 1:
				turn.multiplier = turn.defaultmultiplier
				changes.append(["turn","multipliers"])
		if move != "punch" and move != "combo" and move != "comboend":
			if turn.energy < 3 and move != "defend":
				turn.energy += 1
				changes.append(["turn","energy+",1])
			if turnt.defending and move != "pierce" and move != "kamikaze":
				turnt.energy = min(turnt.energy+2, 3)
				turnt.multiplier += 0.5
				changes.append(["turnt","energy+",2])
				changes.append(["turnt","multipliers"])
		elif turnt.mp < 3 and move != "defend":
			turnt.mp += 1
			changes.append(["turnt","mp+",1])
		if turnt.defending:
			turnt.defending = False
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
		"combo": "{turnt} couldn't even handle half of {turn}'s combo.",
		"comboend": "{turnt} got combo'd right in the gut by {turn}.",
		"pierce": "{turn} pierced {turnt} in the heart.",
		"kamikaze-killself": "{turnt} was destroyed by their own kamikaze, {turn} was confused.",
		"kamikaze": "{turnt} was crippled by {turn}'s kamikaze.",
		"flee": "{turnt} fled like a baby!"
	}

	def getView(self, timeout=False):
		turn = self.core.turn
		timeout = True if timeout or turn.disable or turn.bot else False
		cure, curm = turn.energy, turn.mp
		onee, twoe, onem, one, two, three = (cure < 1), (cure < 2), (curm < 1), (curm != 1), (curm != 2), (curm != 3)

		view = discord.ui.View(timeout=None)
		view.add_item(discord.ui.Button( style=Style.red,      label=f"Punch [{max(cure,1)}]", custom_id="punch",     row=0, disabled=(timeout or onee),  emoji="👊"))
		view.add_item(discord.ui.Button( style=Style.red,      label=f"Combo [2]",             custom_id="combo",     row=0, disabled=(timeout or twoe),  emoji="⛓️"))
		view.add_item(discord.ui.Button( style=Style.red,      label=f"Defend [1]",            custom_id="defend",    row=0, disabled=(timeout or onee),  emoji="🛡️"))
		view.add_item(discord.ui.Button( style=Style.gray,     label=f"Wait",                  custom_id="wait",      row=0, disabled=timeout,            emoji="🕐"))
		view.add_item(discord.ui.Button( style=Style.gray,     label=f"Flee",                  custom_id="flee",      row=0, disabled=timeout,            emoji="✖️"))
		view.add_item(discord.ui.Button( style=Style.blurple,  label=f"Attack-Up [1]",         custom_id="attackup", row=1, disabled=(timeout or one),   emoji="⏫"))
		view.add_item(discord.ui.Button( style=Style.blurple,  label=f"Pierce [2]",            custom_id="pierce",    row=1, disabled=(timeout or two),   emoji="📍"))
		view.add_item(discord.ui.Button( style=Style.blurple,  label=f"Kamikaze [3]",          custom_id="kamikaze",  row=1, disabled=(timeout or three), emoji="💥"))
		view.add_item(discord.ui.Button( style=Style.green,    label=f"Heal [{max(curm,1)}]",  custom_id="heal",      row=1, disabled=(timeout or onem),  emoji="💓"))
		return view
	
	###

	def wait(self, turn:FP, turnt:FP):
		return []

	def punch(self, turn:FP, turnt:FP):
		damage, energyloss = turn.getDamage(punch_damage[turn.energy-1]), turn.energy
		turnt.health, turn.energy = turnt.health-damage, 0
		return [["turnt","health-",damage],["turn","energy-",energyloss]]
	def combo(self, turn:FP, turnt:FP):
		damage = turn.getDamage(combo_damage_1[turn.energy-1])
		turnt.health, turn.comboing, turn.energy = turnt.health-damage, turn.energy, turn.energy-2
		return [["turnt","health-",damage],["turn","energy-",2]]
	def comboend(self, turn:FP, turnt:FP):
		damage = turn.getDamage(combo_damage_2[turn.comboing-1])
		turnt.health, turn.comboing = turnt.health-damage, False
		return [["turnt","health-",damage]]
	def defend(self, turn:FP, turnt:FP):
		turn.defending, turn.energy = True, turn.energy-1
		return [["turn","energy-",1]]

	def attackup(self, turn:FP, turnt:FP):
		turn.multiplier, turn.mp = turn.multiplier+0.5, turn.mp-1
		return [["turn","multipliers"],["turn","mp-",1]]
	def pierce(self, turn:FP, turnt:FP):
		turnt.health, turn.mp, turnt.mp = turnt.health-15, turn.mp-2, turnt.mp-1
		return [["turnt","health-",15],["turnt","mp-",1],["turn","mp-",2]]
	def kamikaze(self, turn:FP, turnt:FP):
		turn.health, turnt.health, turn.mp = turn.health-50, turnt.health-50, turn.mp-3
		return [["turn","health-",50],["turnt","health-",50],["turn","mp-",3]]

	def heal(self, turn:FP, turnt:FP):
		gain, loss = heal_gain[turn.mp-1], turn.mp
		turn.health, turn.mp = turn.health+gain, 0
		return [["turn","health+",gain],["turn","mp-",loss]]
		
def clamp(n, minn, maxn):
	return max(min(maxn, n), minn)
