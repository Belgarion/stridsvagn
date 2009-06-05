import math
class Vertex2: # {{{
	def __init__(self, x, y):
		self.x = x
		self.y = y
	def __str__(self):
		return str((self.x, self.y))
	def __add__(self, v):
		return Vertex2(self.x + v.x, self.y + v.y)
	def __sub__(self, v):
		return Vertex2(self.x - v.x, self.y - v.y)
	def __mul__(self, multiple):
		return Vertex2(self.x * multiple, self.y * multiple)
	__rmul__ = __mul__
	def __div__(self, divisor):
		return Vertex2(1.0 / divisor * self)
	def dot(self, other):
		return self.x*other.x + self.y*other.y
	def magnitude(self):
		return math.sqrt(self.x*self.x + self.y*self.y)
	def normalize(self):
		inverse_magnitude = 1.0/self.magnitude()
		return Vertex2(self.x*inverse_magnitude, self.y*inverse_magnitude)
	def perpendicular(self):
		return Vertex2(-self.y, self.x)
	def __getitem__(self, key):
		if key == 0:
			return self.x
		elif key == 1:
			return self.y
#}}}
