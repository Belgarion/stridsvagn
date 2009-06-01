from Vertex2 import *
class GameObject: #{{{
	def __init__(self, x, y, width, height, angle = 0.0, type = None):
		self.position = Vertex2(x, y)
		self.width = width
		self.height = height
		self.angle = angle
		self.type = type
		if width > height: 
			self.size = width
		else:
			self.size = height
#}}}
