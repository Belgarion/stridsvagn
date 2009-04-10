class Projection: #{{{
	def __init__(self, min, max):
		self.min, self.max = min, max
	def intersects(self, other):
		return self.max > other.min and other.max > self.min
#}}}
