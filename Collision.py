import math
from Polygon import *
from Vertex2 import *
def Intersect(rect1, rect2): #{{{
	Width = rect1[2].x * 2
	hw = Width/2 #half width
	Height = rect1[2].y * 2
	hh = Height/2 #half height
	#A = math.radians(rect1[1])
	A = rect1[1]
	sina = math.sin(A)
	cosa = math.cos(A)

	ul1 = Vertex2(rect1[0].x - hw*cosa - hh*sina, rect1[0].y + hh*cosa - hw*sina)
	ur1 = Vertex2(rect1[0].x + hw*cosa - hh*sina, rect1[0].y + hh*cosa + hw*sina)
	dl1 = Vertex2(rect1[0].x - hw*cosa + hh*sina, rect1[0].y - hh*cosa - hw*sina)
	dr1 = Vertex2(rect1[0].x + hw*cosa + hh*sina, rect1[0].y - hh*cosa + hw*sina)

	Width = rect2[2].x * 2
	hw = Width/2 #half width
	Height = rect2[2].y * 2
	hh = Height/2 #half height
	#A = math.radians(rect2[1])
	A = rect2[1]
	sina = math.sin(A)
	cosa = math.cos(A)

	ul2 = Vertex2(rect2[0].x - hw * cosa - hh * sina, rect2[0].y + hh * cosa - hw*sina)
	ur2 = Vertex2(rect2[0].x + hw * cosa - hh * sina, rect2[0].y + hh * cosa + hw*sina)
	dl2 = Vertex2(rect2[0].x - hw * cosa + hh * sina, rect2[0].y - hh * cosa - hw*sina)
	dr2 = Vertex2(rect2[0].x + hw * cosa + hh * sina, rect2[0].y - hh * cosa + hw*sina)

	points1 = [ul1, ur1, dr1, dl1]
	points2 = [ul2, ur2, dr2, dl2]
	p1 = Polygon(points1)
	p2 = Polygon(points2)

	return p1.intersects(p2)
#}}}
