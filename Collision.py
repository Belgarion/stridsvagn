import math
from Polygon import *
from Vertex2 import *
from GameObject import *
def Intersect(obj1, obj2): #{{{
	Width = obj1.width
	hw = Width/2 #half width
	Height = obj1.height
	hh = Height/2 #half height
	A = math.radians(float(obj1.angle))
	sina = math.sin(A)
	cosa = math.cos(A)

	ul1 = Vertex2(obj1.position.x - hw*cosa - hh*sina, obj1.position.y + hh*cosa - hw*sina)
	ur1 = Vertex2(obj1.position.x + hw*cosa - hh*sina, obj1.position.y + hh*cosa + hw*sina)
	dl1 = Vertex2(obj1.position.x - hw*cosa + hh*sina, obj1.position.y - hh*cosa - hw*sina)
	dr1 = Vertex2(obj1.position.x + hw*cosa + hh*sina, obj1.position.y - hh*cosa + hw*sina)

	Width = obj2.width
	hw = Width/2 #half width
	Height = obj2.height
	hh = Height/2 #half height
	A = math.radians(float(obj2.angle))
	sina = math.sin(A)
	cosa = math.cos(A)

	ul2 = Vertex2(obj2.position.x - hw * cosa - hh * sina, obj2.position.y + hh * cosa - hw*sina)
	ur2 = Vertex2(obj2.position.x + hw * cosa - hh * sina, obj2.position.y + hh * cosa + hw*sina)
	dl2 = Vertex2(obj2.position.x - hw * cosa + hh * sina, obj2.position.y - hh * cosa - hw*sina)
	dr2 = Vertex2(obj2.position.x + hw * cosa + hh * sina, obj2.position.y - hh * cosa + hw*sina)

	points1 = [ul1, ur1, dr1, dl1]
	points2 = [ul2, ur2, dr2, dl2]
	p1 = Polygon(points1)
	p2 = Polygon(points2)

	return p1.intersects(p2)
#}}}
def CheckCollision(arr1, arr2): #{{{
	if (type(arr1) != type([])):
		arr1 = [arr1]
	if (type(arr2) != type([])):
		arr2 = [arr2]

	for obj1 in arr1:
		for obj2 in arr2:
			dist = obj1.position - obj2.position
			distance = (dist.x ** 2) + (dist.y ** 2)

			if distance < (obj1.size/2 + obj2.size/2 + 0.5) ** 2:
				if Intersect(obj1, obj2): return True

	return False
#}}}
