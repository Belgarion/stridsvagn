#!/usr/bin/env python
#{{{ Imports
import socket
import thread
import sys
import time
import cPickle
import math
import traceback

from OpenGL.GL import *
from OpenGL.GLU import *

from math import radians
import pygame
import pygame.image
import pygame.font
from pygame.locals import *
#}}}
#{{{ Globals
HOST = 'localhost'
PORT = 30000
BUFSIZ = 65535
ADDR = (HOST, PORT)
x = 0
y = 0
wireframe = False
angle = 0
towerAngle = 45
PLAYERS = {}
SHOTS = {}
speedForward = 2
speedBackward = 2
backgroundColor = (68, 68, 68)
fps = 0
scrollback = []
id = 0
LEVEL = []
DOTS= [] #debug-dots
#}}}
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
# }}}
class Projection: #{{{
	def __init__(self, min, max):
		self.min, self.max = min, max
	def intersects(self, other):
		return self.max > other.min and other.max > self.min
# }}}
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
def glDot(v, color = []): #{{{
	glLoadIdentity()
	if color == []:
		glColor3f(1.0, 1.0, 1.0)
	else:
		glColor3f(color[0], color[1], color[2])
	glTranslate(v.x, v.y, 0.0)
	glBegin(GL_QUADS)
	glVertex3f(-1, 1, 0.0)
	glVertex3f( 1, 1, 0.0)
	glVertex3f( 1,-1, 0.0)
	glVertex3f(-1,-1, 0.0)
	glEnd()
# }}}
def Intersect(rect1, rect2): #{{{
	global DOTS
	DOTS = []

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

	#DOTS.append(ul1)
	#DOTS.append(ul2)
	#DOTS.append(ur1)
	#DOTS.append(ur2)
	#DOTS.append(dl1)
	#DOTS.append(dl2)
	#DOTS.append(dr1)
	#DOTS.append(dr2)

	return p1.intersects(p2)
# }}}
class Text: #{{{
	def __init__(self):
		pygame.font.init()
		if not pygame.font.get_init():
			print "Could not init font renderer"
			return

		self.font = pygame.font.Font("font.ttf", 16)
		self.char = []
		self.index = glGenLists(256)
		for c in range(256):
			self.char.append(self.createCharacter(self.index + c, chr(c)))
		self.char = tuple(self.char)
		self.lw = self.char[ord('0')][1]
		self.lh = self.char[ord('0')][2]

	def createCharacter(self, index, s):
		try:
			letter_render = self.font.render(s, 1, (255,255,255), (0,0,0))
			letter = pygame.image.tostring(letter_render, 'RGBA', 1)
			letter_w, letter_h = letter_render.get_size()

			letter_arr = list(letter)
			i = 0
			while i < len(letter_arr):
				if letter_arr[i] == '\x00' and letter_arr[i+1] == '\x00' and letter_arr[i+2] == '\x00':
					letter_arr[i+3] = '\x00'
				i += 4
			letter = ''.join(letter_arr)


			label_texture = glGenTextures(1)
			glBindTexture(GL_TEXTURE_2D, label_texture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, letter_w, letter_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, letter)

			glNewList(index, GL_COMPILE)
			glBindTexture(GL_TEXTURE_2D, label_texture)
			glBegin(GL_QUADS)
			glTexCoord2f(0, 0); glVertex2f(0, 0)
			glTexCoord2f(0, 1); glVertex2f(0, letter_h)
			glTexCoord2f(1, 1); glVertex2f(letter_w, letter_h)
			glTexCoord2f(1, 0); glVertex2f(letter_w, 0)
			glEnd()
			glEndList()
			
		except Exception, e:
			letter_w = 0
			letter_h = 0
			index = None

		return (index, letter_w, letter_h)

	def Print(self, s, x, y, z = -61.0, color = (1.0, 1.0, 1.0)):
		s = str(s)
		i = 0
		lx = 0
		length = len(s)

		glEnable(GL_TEXTURE_2D)
		#glColor4f(1.0, 1.0, 1.0, 1.0)
		glColor3fv(color)
		while i < length:
			ch = self.char[ord(s[i])]
			glLoadIdentity()
			glTranslatef(x + lx, y, z)
			glCallList(ch[0])
			lx += ch[1]
			i += 1
		glDisable(GL_TEXTURE_2D)
	def createTexDL(self, texture, width, height):

		return newList

	def DrawFPS(self, fps):
		self.Print(fps, width/2 - self.lw * len(str(fps)), height/2 - self.lh)
#}}}
def send(data): #{{{
	try:
		sock.sendto(data + "\x00", ADDR)
	except Exception, e:
		print "Send failed"
		traceback.print_exc()
		sock.close()
		exit(0)
#}}}
def recv_data(): #{{{
	global PLAYERS, SHOTS, LEVEL, scrollback, x, y
	t = time.time()
	while not quit:
		try:
			recv_data = sock.recv(BUFSIZ)
		except:
			print "Server closed connection, thread exiting"
			thread.interrupt_main()
			break

		if not recv_data:
			print "Server closed connection, thread exiting"
			thread.interrupt_main()
			break
		else:
			commands = recv_data.split("\x00")
			for c in commands:
				if len(c) == 0:
					continue
				if c[0] == "P":
					send(c)
				elif c[0:3] == "GPA":
					playerslock.acquire()
					PLAYERS = cPickle.loads(c[3:])
					playerslock.release()
				elif c[0:3] == "GPS":
					SHOTS = cPickle.loads(c[3:])
				elif c[0] == "C":
					scrollback.insert(0, "Chat: " + str(c[1:]))
					print "Chat: ", c[1:]
				elif c[0] == "S":
					print "Server message: ", c[1:]
					lines = c[1:].split('\n')
					for line in lines:
						scrollback.insert(0, line)
				elif c[0] == "L":
					LEVEL = cPickle.loads(c[1:])
				elif c[0] == "I":
					id = c[1:]
				else:
					lines = c.split('\n')
					for line in lines:
						scrollback.insert(0, line)
					print "Received: \n", c

		if time.time() - t >= 1.0/100:
			send('M ' + str(x) + ' ' + str(y) + ' ' + str(angle) + ' ' + str(int(towerAngle)))
			t = time.time()
#}}}
def send_data(): #{{{
	while 1:
		send_data = str(raw_input("> "))
		if len(send_data) == 0: continue
		if send_data[0] != '\\':
			send_data = '\\' + send_data
		send(send_data)
#}}}
#{{{ Rendering
def displayConsole(): #{{{
	cw = width
	ch = height/2
	glLoadIdentity()
	glBegin(GL_QUADS)
	glColor4f(0.0, 0.0, 0.0, 0.8)
	glVertex3f(-cw, ch, 0.0)
	glVertex3f(-cw, 0.0, 0.0)
	glVertex3f( cw, 0.0, 0.0)
	glVertex3f( cw, ch, 0.0)
	glEnd()

	line = 0
	text.Print('> ' + cmd, -cw/2, text.lh * line, 0.0)
	for str in scrollback[:int(ch / text.lh)-1]:
		line += 1
		text.Print(str, -cw/2, text.lh * line, 0.0)
#}}}
def displayPlayerList(): #{{{
	lx = -width/2 + 50
	ly = -height/2 + 50
	lw = width - 100
	lh = height - 100
	tx = lx + 30
	ty = ly + lh - 20
	coly = (1.0, 1.0, 0.0)
	colgr = (0.6, 0.6, 0.6)
	glLoadIdentity()
	glCallList(plist)

	i = 3
	for p in PLAYERS:
		i += 1
		cly = ty -5 - i*text.lh

		if p['id'] == id:
			glLoadIdentity()
			glBegin(GL_QUADS)
			glColor4f(1.0, 1.0, 1.0, 0.2)
			glVertex3f(lx + 6, cly + text.lh, 0.0)
			glVertex3f(lx + lw - 6, cly + text.lh, 0.0)
			glVertex3f(lx + lw - 6, cly - text.lh, 0.0)
			glVertex3f(lx + 6, cly - text.lh, 0.0)
			glEnd()

		text.Print(0, tx + (5-len(str(0)))*text.lw, cly, 0.1, coly)
		if p['ping'] < 80: pingcolor = (0.0, 1.0, 0.0)
		elif p['ping'] < 140: pingcolor = coly
		else: pingcolor = (1.0, 0.0, 0.0)
		text.Print(str(p['ping']), tx + (16-len(str(p['ping'])+"ms"))*text.lw, cly, 0.1, pingcolor)
		text.Print("ms", tx + (16-len("ms"))*text.lw, cly, 0.1)
		text.Print(p['id'], tx + 20*text.lw, cly, 0.1)
		text.Print(p['name'], tx + 26*text.lw, cly, 0.1)

		i+= 1
		cly -= text.lh

		text.Print(0, tx + (5-len(str(0)))*text.lw, cly, 0.1, colgr)
		text.Print("0%", tx + (16-len(str(0)+"%"))*text.lw, cly, 0.1)
#}}}

frames = 0
t = time.time()
def render(): #{{{
	global t, frames, fps
	
	if wireframe:
		glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
	else:
		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho((-width/2)*zoom, (width/2)*zoom, (-height/2)*zoom, (height/2)*zoom, -1.0, 100.0)
	glMatrixMode(GL_MODELVIEW)

	for obj in LEVEL[1]:
		if obj['type'] == '#':
			glLoadIdentity()
			glTranslate( obj['position'][0], obj['position'][1], -60.0)
			glBegin(GL_QUADS)
			glColor3f(1.0, 1.0, 1.0)
			glVertex3f(-1,1,1)
			glVertex3f(1,1,1)
			glVertex3f(1,-1,1)
			glVertex3f(-1,-1,1)
			glEnd()
			glBegin(GL_QUADS)
			glColor3f(0.0, 0.5, 1.0)
			glVertex3f(-5, 5, 0.0)
			glVertex3f( 5, 5, 0.0)
			glVertex3f( 5,-5, 0.0)
			glVertex3f(-5,-5, 0.0)
			glEnd()

	playerslock.acquire()
	for p in PLAYERS:
		#tank
		glLoadIdentity()
		glTranslate(float(p['position'][0]), float(p['position'][1]), -60.0)
		glRotatef(int(p['angle']), 0.0, 0.0, 1.0)
		glColor3fv(p['color'])
		glCallList(tl)

		#tower
		glLoadIdentity()
		glTranslate(float(p['position'][0]), float(p['position'][1]), -60.0)
		glRotatef(float(p['towerAngle']), 0.0, 0.0, 1.0)
		glColor3f(0.0, 0.6, 0.0)
		glCallList(tower)
	playerslock.release()

	for s in SHOTS:
		glLoadIdentity()
		glTranslate(float(s['position'][0]), float(s['position'][1]), -60.0)
		glRotatef(int(s['angle']), 0.0, 0.0, 1.0)

		glBegin(GL_QUADS)
		glColor3fv(s['color'])
		glVertex3f(-1, 2, 0.0)
		glVertex3f( 1, 2, 0.0)
		glVertex3f( 1,-2, 0.0)
		glVertex3f(-1,-2, 0.0)
		glEnd()

	for d in DOTS:
		glDot(d)

	#debug linje (aimlinje)
	glLoadIdentity()
	glBegin(GL_LINES)
	glColor3f(0.0, 1.0, 1.0)
	glVertex3f(x, y, -61.0)
	glVertex3f(mx, my, -61.0)
	glEnd()

	text.DrawFPS("FPS: %d" % fps)

	if showPlayerList: displayPlayerList()
	if showConsole: displayConsole()

	glFlush()
	pygame.display.flip()

	frames += 1
	if (time.time() - t >= 1):
		seconds = (time.time() - t)
		fps = frames/seconds
		t = time.time()
		frames = 0
#}}}
#}}}
#{{{ Initialization
def initGL(): #{{{
	buildLists()

	glShadeModel(GL_SMOOTH)
	r = float(backgroundColor[0])/255
	g = float(backgroundColor[1])/255
	b = float(backgroundColor[2])/255
	glClearColor(r, g, b, 0.0)
	glClearDepth(1.0)
	glEnable(GL_DEPTH_TEST)
	glDepthFunc(GL_LEQUAL)
	glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

	glViewport(0, 0, width, height)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho(-width/2, width/2, -height/2, height/2, -1.0, 100.0)

	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

	glEnable(GL_LINE_SMOOTH)

	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
#}}}
def buildLists(): #{{{
	global tl, tower, plist

	tl = glGenLists(3)
	glNewList(tl, GL_COMPILE)
	glBegin(GL_TRIANGLE_STRIP)
	glVertex3f(-21,  10.5, 0.0) #v1
	glVertex3f(-21, -10.5, 0.0) #v2
	glVertex3f( 21,  10.5, 0.0) #v3

	glVertex3f(-21, -10.5, 0.0) #v2
	glVertex3f( 21,  10.5, 0.0) #v3
	glVertex3f( 21, -10.5, 0.0) #v4
	glEnd()
	glEndList()

	tower = tl + 1
	glNewList(tower, GL_COMPILE)
	glBegin(GL_TRIANGLE_STRIP)
	glVertex3f(-2.25, -22.5, 0.0) #v1
	glVertex3f(-2.25, -6.75, 0.0) #v2
	glVertex3f( 2.25, -6.75, 0.0) #v3

	glVertex3f(-2.25, -22.5, 0.0) #v1
	glVertex3f( 2.25, -6.75, 0.0) #v3
	glVertex3f( 2.25, -22.5, 0.0) #v4
	glEnd()

	glBegin(GL_TRIANGLE_STRIP)
	glVertex3f(-6.75, -6.75, 0.0) #v1
	glVertex3f(-6.75,  6.75, 0.0) #v2
	glVertex3f( 6.75,  6.75, 0.0) #v3

	glVertex3f(-6.75, -6.75, 0.0) #v1
	glVertex3f( 6.75,  6.75, 0.0) #v3
	glVertex3f( 6.75, -6.75, 0.0) #v4
	glEnd()
	glEndList()

	plist = tl + 2
	glNewList(plist, GL_COMPILE)
	lx = -width/2 + 50
	ly = -height/2 + 50
	lw = width - 100
	lh = height - 100
	glLoadIdentity()
	glBegin(GL_QUADS)
	glColor4f(0.0, 0.0, 0.0, 0.5)
	glVertex3f( lx, ly + lh, 0.0)
	glVertex3f( lx, ly, 0.0)
	glVertex3f( lx + lw, ly, 0.0)
	glVertex3f( lx + lw, ly + lh, 0.0)
	glEnd()

	#border
	lineWidth = glGetFloatv(GL_LINE_WIDTH)
	glLineWidth(6)
	glBegin(GL_LINES)
	glVertex3f(lx + 3, ly + lh, 0.0)
	glVertex3f(lx + 3, ly, 0.0)
	
	glVertex3f(lx + lw - 3, ly, 0.0)
	glVertex3f(lx + lw - 3, ly + lh, 0.0)

	glVertex3f(lx + 6, ly + 3, 0.0)
	glVertex3f(lx + lw - 6, ly + 3, 0.0)
	
	glVertex3f(lx + 6, ly + lh - 3, 0.0)
	glVertex3f(lx + lw - 6, ly + lh - 3, 0.0)
	glEnd()
	glLineWidth(lineWidth)
	#end border


	tx = lx + 30
	ty = ly + lh - 20

	# Header
	glBegin(GL_QUADS)
	glColor4f(0.0, 0.0, 0.0, 0.2)
	glVertex3f(lx + 6, ly + lh - 6, 0.0)
	glVertex3f(lx + lw - 6, ly + lh - 6, 0.0)
	glVertex3f(lx + lw - 6, ty - 2*text.lh - 5, 0.0)
	glVertex3f(lx + 6, ty - 2*text.lh - 5, 0.0)
	glEnd()


	coly = (1.0, 1.0, 0.0)
	colgr = (0.6, 0.6, 0.6)

	i = 1
	cly = ty - i*text.lh
	text.Print("Score", tx, cly, 0.1, coly)
	text.Print("Ping", tx + 12*text.lw, cly, 0.1, coly)
	i += 1
	cly -= text.lh
	text.Print("Kills", tx, cly, 0.0, coly)
	text.Print("Loss", tx + 12*text.lw, cly, 0.1, coly)
	text.Print("ID", tx + 20*text.lw, cly, 0.1, coly)
	text.Print("Name", tx + 26*text.lw, cly, 0.1, coly)
	# end header

	glEndList()
#}}}
#}}}
def collision(x, y, angle): #{{{
	tank_pos = Vertex2(x, y)
	tank_size = 42.0
	obj_size = 10.0
	for obj in LEVEL[1]:
		lx, ly = obj['position']
		obj_pos = Vertex2(lx, ly)
		dist = tank_pos - obj_pos
		distance = math.sqrt((dist.x * dist.x) + (dist.y * dist.y))

		if distance < tank_size/2 + obj_size/2 + 0.5:
			a = [tank_pos, math.radians(angle), Vertex2(21.0, 10.5)]
			b = [obj_pos, math.radians(0.0), Vertex2(5.0,5.0)]
			collision = Intersect(a,b)
			if collision: return True

	return False
#}}}
def checkMove(direction): #{{{
	global x, y

	oldx, oldy = x, y
	if direction == "BACKWARD":
		x += math.sin(math.radians(angle-90)) * speedBackward
		y -= math.cos(math.radians(angle-90)) * speedBackward
	elif direction == "FORWARD":
		x -= math.sin(math.radians(angle-90)) * speedForward
		y += math.cos(math.radians(angle-90)) * speedForward
	
	if x < -width/2 or x > width/2 or y < -height/2 or y > height/2 or collision(x, y, angle):
		x, y = oldx, oldy
#}}}
def rotate(direction): #{{{
	global angle
	oldAngle = angle
	if direction == "RIGHT":
		angle -= 1
		if angle == -1: angle = 360
	else:
		angle = (angle + 1) % 360
	if collision(x,y,angle): angle = oldAngle

#}}}
def handleInput(): #{{{
	global quit, showPlayerList, my, mx, x, y, angle, towerAngle, wireframe, zoom, showConsole, cmd, scrollback
	scrollback = []
	commands = ['']
	cmd_index = -1
	cmd = ''
	zoom = 1
	my = 0;
	mx = 0
	t = time.time()
	st = time.time()
	while not quit:
		try:
			if not showConsole:
				for event in pygame.event.get():
					if event.type == MOUSEMOTION:
						(mx, my) = event.pos
						mx = mx - width/2
						my = height - my - height/2
					elif event.type == QUIT: quit = True
					elif event.type == KEYUP:
						if event.key == K_TAB: showPlayerList = False
						elif event.key == K_F9: wireframe = not wireframe
					elif event.type == KEYDOWN:
						if event.key == K_TAB: showPlayerList = True
						elif event.key == 167: showConsole = True
						elif event.key == K_ESCAPE: quit = True
					elif event.type == MOUSEBUTTONDOWN:
						if event.button == 4:
							zoom += 0.1
							if zoom == 0: zoom = 0.1
						elif event.button == 5:
							zoom -= 0.1
							if zoom == 0: zoom = -0.1

				mousePressed = pygame.mouse.get_pressed()
				if mousePressed[0]:
					if time.time() - st > 1.0/10:
						st = time.time()
						send("S " + str(int(towerAngle)))

				towerAngle = math.degrees(math.atan2(my - y, mx - x)) + 90

				pressed = pygame.key.get_pressed()
				if pressed[K_RIGHT]:
					rotate("RIGHT")
				elif pressed[K_LEFT]: 
					rotate("LEFT")

				if pressed[K_DOWN]:
					checkMove("BACKWARD")
				elif pressed[K_UP]:
					checkMove("FORWARD")
				elif pressed[K_j]:
					y += 1
					collision(x,y,angle)
				elif pressed[K_k]:
					y -= 1
					collision(x,y,angle)


				if pressed[ord('x')]: print x
				if pressed[ord('y')]: print y
				if pressed[ord('a')]: print angle

			else:
				pressed = pygame.key.get_pressed()

				for event in pygame.event.get():
					if event.type == KEYDOWN:
						if event.key == 167 or event.key == K_ESCAPE: showConsole = False
						elif event.key == K_UP:
							cmd_index = (cmd_index + 1) % len(commands)
							cmd = commands[cmd_index]
						elif event.key == K_DOWN:
							cmd_index = (cmd_index - 1) % -len(commands)
							cmd = commands[cmd_index]
						elif event.key == K_RETURN:
							if len(cmd) == 0: continue
							if cmd[0] != '\\':
								cmd = '\\' + cmd
 
							runCmd(cmd)

							scrollback.insert(0,cmd)
							commands.insert(0, cmd)
							cmd = ''
							cmd_index = -1
						elif event.key == K_DELETE or event.key == K_TAB: pass
						elif event.key == K_BACKSPACE:
							t = time.time()
							cmd = cmd[:-1]
						else: 
							cmd += event.unicode.encode('latin1')

				if time.time() - t >= 0.13:
					t = time.time()
					if pressed[K_BACKSPACE]: cmd = cmd[:-1]


			time.sleep(0.01)
		except:
			traceback.print_exc()
#}}}
def runCmd(cmd): #{{{
	global quit

	cmdl = cmd.lower()[1:]
	if cmdl == "quit":
		quit = True
	else:
		send(cmd)
#}}}
if __name__ == "__main__": #{{{
	width = 800
	height = 600
	quit = False
	nick = 'Player'

	showPlayerList = False
	showConsole = False

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.sendto('C' + nick, ADDR)
	sock.sendto('GL', ADDR)

	sendlock = thread.allocate_lock()

	thread.start_new_thread(recv_data, ())
	thread.start_new_thread(send_data, ())
	playerslock = thread.allocate_lock()

	pygame.init()
	pygame.display.init()
	screen = pygame.display.set_mode((width, height), HWSURFACE | HWPALETTE | OPENGL | DOUBLEBUF)
	pygame.display.set_caption("Stridsvagn")

	text = Text()
	initGL()

	thread.start_new_thread(handleInput, ())

	lastRender = time.time()

	try:
		time.sleep(0.1)
		while not quit:
			if True:#time.time() - lastRender > 1.0/100:
				lastRender = time.time()
				render()
			else:
				#time.sleep(0.01)
				pass

	except Exception, e:
		traceback.print_exc()
	finally:
		time.sleep(1)
		send("\\quit")
		sock.close()
		pygame.font.quit()
		pygame.display.quit()
#}}}
