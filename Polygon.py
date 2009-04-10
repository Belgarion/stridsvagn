from Projection import *
class Polygon: #{{{
	def __init__(self, points):
		"""points is a list of Vectors"""
		self.points = points
		
		# Build a list of the edge vectors
		self.edges = []
		for i in range(len(points)):
			point = points[i]
			next_point = points[(i+1)%len(points)]
			self.edges.append(next_point - point)
	def project_to_axis(self, axis):
		"""axis is the unit vector (vector of magnitude 1) to project the polygon onto"""
		projected_points = []
		for point in self.points:
			# Project point onto axis using the dot operator
			projected_points.append(point.dot(axis))
		return Projection(min(projected_points), max(projected_points))
	def intersects(self, other):
		"""returns whether or not two polygons intersect"""
		# Create a list of both polygons' edges
		edges = []
		edges.extend(self.edges)
		edges.extend(other.edges)
		
		for edge in edges:
			axis = edge.normalize().perpendicular() # Create the separating axis (see diagrams)
			
			# Project each to the axis
			self_projection = self.project_to_axis(axis)
			other_projection = other.project_to_axis(axis)
			
			# If the projections don't intersect, the polygons don't intersect
			if not self_projection.intersects(other_projection):
				return False
		
		# The projections intersect on all axes, so the polygons are intersecting
		return True
# }}}
