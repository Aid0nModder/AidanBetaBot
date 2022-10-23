class movecls():
	def __init__(self, call, label):
		self.label = label
		self.call = call

	def callreal(self):
		self.call(self)

def move(label:str="default"):
	def decorator(orig_func):
		return movecls(call=orig_func, label=label)
	return decorator

@move(label="wddawdwa")
def test(self):
	print(self.label)

test.callreal()