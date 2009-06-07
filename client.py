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

from Vertex2 import *
from Collision import *
from GameObject import *
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
futureTowerAngle = 45
PLAYERS = {}
SHOTS = {}
KILLED_TANKS = []
speedForward = 2
speedBackward = 2
backgroundColor = (68, 68, 68)
fps = 0
scrollback = []
id = 0
DOTS= [] #debug-dots
zoom = 1
(mx, my) = (0,0)
shootTime = time.time()
#}}}
class Level: #{{{
	def __init__(self, name, objs):
		self.name = name
		self.objs = objs
#}}}
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
#}}}
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
		letter_w = 0
		letter_h = 0
		try:
			letter_render = self.font.render(s, True, (255,255,255), (0,0,0))
			letter = pygame.image.tostring(letter_render, 'RGBA', True)
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
			index = None

		return (index, letter_w, letter_h)

	def Print(self, s, x, y, z = -61.0, color = (1.0, 1.0, 1.0)):
		s = str(s)
		length = len(s)

		if (type(self.char[ord(s[0])][0]) != type(0)): #failsafe
			glRasterPos3f(x, y, z)
			text_render = self.font.render(s, True, (color[0]*255, color[1]*255, color[2]*255), (0,0,0))
			text_img = pygame.image.tostring(text_render, 'RGBA', True)
			text_w, text_h = text_render.get_size()
			
			text_arr = list(text_img)
			i = 0
			while (i < len(text_arr)):
				if (text_arr[i] == '\x00' and text_arr[i+1] == '\x00' and text_arr[i+2] == '\x00'):
					text_arr[i+3] = '\x00'
				i += 4
			text_img = ''.join(text_arr)

			glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, text_img)
		else:
			i = 0
			lx = 0

			glColor3fv(color)
			glEnable(GL_TEXTURE_2D)
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
	global PLAYERS, SHOTS, LEVEL, scrollback, x, y, id
	t = time.time()
	buf = ''
	while not quit:
		try:
			recv_data = sock.recv(BUFSIZ)
			buf += recv_data
		except:
			print "Server closed connection, thread exiting"
			thread.interrupt_main()
			break

		if not recv_data:
			print "Server closed connection, thread exiting"
			thread.interrupt_main()
			break
		else:
			commands = []
			while len(buf) > 0:
				index = buf.find("\x00")
				if index == -1: break
				commands.append(buf[:index])
				buf = buf[index+1:]

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
				elif c[0:2] == "FU":
					(x, y) = cPickle.loads(c[2:])
				elif c[0] == "S":
					print "Server message: ", c[1:]
					lines = c[1:].split('\n')
					for line in lines:
						scrollback.insert(0, line)
				elif c[0] == "L":
					tmp = cPickle.loads(c[1:])
					objs = []
					for obj in tmp[1]:
						objs.insert(0, GameObject(obj['position'][0], obj['position'][1], 10.0, 10.0, 0.0, obj['type']))
					LEVEL = Level(tmp[0], objs)
				elif c[0:2] == "KT":
					tmp = cPickle.loads(c[2:])
					for obj in tmp:
						KILLED_TANKS.append(obj)
				elif c[0] == "I":
					id = c[1:]
				elif c[0] == "K":
					# get this when someone gets killed: killer id|victim id|x|y|angle|towerangle|hitAtX|hitAtY|rcolor|gcolor|bcolor
					tmp = cPickle.loads(c[1:])

					killerId = tmp[0]
					victimId = tmp[1]
					victimHitAtX = c[2]
					victimHitAtY = c[3]
					
					KILLED_TANKS.append(tmp[4])
					
					namesFound = 0
					for p in PLAYERS:
						if int(p['id']) == int(killerId):
							killerName = p['name']
							namesFound += 1
						if int(p['id']) == int(victimId):
							victimName = p['name']
							namesFound += 1
						if namesFound == 2:
							break
					print killerName, " killed ", victimName
 
				else:
					lines = c.split('\n')
					for line in lines:
						scrollback.insert(0, line)
					print "Received: \n", c

		if time.time() - t >= 1.0/30:
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
	if (text.lh == 0):
		print "Text height is zero, cannot display console"
		global showConsole
		showConsole = False
		return

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

		text.Print(str(p['score']), tx + (5-len(str(0)))*text.lw, cly, 0.1, coly)
		if p['ping'] < 80: pingcolor = (0.0, 1.0, 0.0)
		elif p['ping'] < 140: pingcolor = coly
		else: pingcolor = (1.0, 0.0, 0.0)
		text.Print(str(p['ping']), tx + (16-len(str(p['ping'])+"ms"))*text.lw, cly, 0.1, pingcolor)
		text.Print("ms", tx + (16-len("ms"))*text.lw, cly, 0.1)
		text.Print(p['id'], tx + 20*text.lw, cly, 0.1)
		text.Print(p['name'], tx + 26*text.lw, cly, 0.1)

		i+= 1
		cly -= text.lh

		text.Print(str(p['kills']), tx + (5-len(str(0)))*text.lw, cly, 0.1, colgr)
		text.Print("0%", tx + (16-len(str(0)+"%"))*text.lw, cly, 0.1)
#}}}

frames = 0
t = time.time()
def render(): #{{{
	global t, frames, fps, towerAngle, futureTowerAngle
	
	if wireframe:
		glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
	else:
		glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho((-width/2)*zoom, (width/2)*zoom, (-height/2)*zoom, (height/2)*zoom, -1.0, 100.0)
	glMatrixMode(GL_MODELVIEW)

	for obj in LEVEL.objs:
		if obj.type == '#':
			glLoadIdentity()
			glTranslate(obj.position.x, obj.position.y, -60.0)
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

	for k in KILLED_TANKS:
		#tank
		glLoadIdentity()
		glTranslate(float(k['position'][0]), float(k['position'][1]), -60.0)
		glRotatef(int(k['angle']), 0.0, 0.0, 1.0)
		glColor3fv(k['color'])
		glCallList(tl)

		#tower
		glLoadIdentity()
		glTranslate(float(k['position'][0]), float(k['position'][1]), -60.0)
		glRotatef(float(k['towerAngle']), 0.0, 0.0, 1.0)
		glColor3f(0.0, 0.2, 0.0)
		glCallList(tower)


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


	twrAng = (towerAngle + 90) % 360
	futTwrAng = (futureTowerAngle + 90) % 360
	diffAng = (futTwrAng - twrAng) % 360
	if diffAng > 180: diffAng = diffAng -360
	seconds = time.time() - t
	if seconds >= 1/30:
		if diffAng > 1.25:
			diffAng = 1.25
		if diffAng < -1.25:
			diffAng = -1.25
		towerAngle += diffAng

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
def collision(tank1x, tank1y, angle): #{{{
	global x, y
	tank_pos = Vertex2(tank1x, tank1y)
	tank_size = 42.0
	
	a = GameObject(tank1x, tank1y, 42.0, 21.0, angle)
	(obj1, obj2) = CheckCollision(a, LEVEL.objs)
	if obj1 != None: return True
	
	p2 = []
	for p in PLAYERS:
		if int(p['id']) == int(id):
			me = p
			continue
		p2.append(GameObject(p['position'][0], p['position'][1], 42.0, 21.0, p['angle']))
		
	for k in KILLED_TANKS:
		p2.append(GameObject(k['position'][0], k['position'][1], 42.0, 21.0, k['angle']))

	(obj1, obj2) = CheckCollision(a, p2)
	if obj2 != None:
		# This is so that tanks do not get stuck into each other.
		tank2pos = obj2.position
		x1, y1, x2, y2 = tank_pos.x, tank_pos.y, tank2pos.x, tank2pos.y
		angle = math.atan2(y2 - y1, x2 - x1) * 180 / math.pi # Get angle
		x -= math.sin(math.radians(angle+90)) * speedForward # NOTE: speedForward could be wrong here. It is more the rotating speed maybe.
		y += math.cos(math.radians(angle+90)) * speedForward
		
		return True

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
	global angle, towerAngle
	oldAngle = angle
	oldTowerAngle = towerAngle
	if direction == "RIGHT":
		angle -= 1
		towerAngle += angle - oldAngle
		if angle == -1: 
			angle = 360
			towerAngle += angle - oldAngle # Is this correct? 
	else:
		angle = (angle + 1) % 360
		towerAngle += angle - oldAngle
	if collision(x,y,angle): 
		angle = oldAngle
		towerAngle = oldTowerAngle
		
#}}}
def handleMouse(): #{{{
	global showConsole, mx, my, towerAngle, futureTowerAngle, zoom, shootTime

	if showConsole: return

	try:
		for event in pygame.event.get([MOUSEMOTION,MOUSEBUTTONDOWN,MOUSEBUTTONUP]):
			if event.type == MOUSEMOTION:
				(mx, my) = event.pos
				mx = mx - width/2
				my = height - my - height/2
			elif event.type == MOUSEBUTTONDOWN:
				if event.button == 4:
					zoom += 0.1
					if zoom == 0: zoom = 0.1
				elif event.button == 5:
					zoom -= 0.1
					if zoom == 0: zoom = -0.1

		futureTowerAngle = math.degrees(math.atan2(my - y, mx - x)) + 90
		

		mousePressed = pygame.mouse.get_pressed()
		if mousePressed[0]:
			if time.time() - shootTime > 1.0:
				shootTime = time.time()
				send("S " + str(int(towerAngle)))
	except:
		traceback.print_exc()
#}}}
def handleInput(): #{{{
	global quit, showPlayerList, x, y, angle, wireframe, showConsole, cmd, scrollback
	scrollback = []
	commands = ['']
	cmd_index = -1
	cmd = ''
	t = time.time()

	while not quit:
		try:
			if (sys.platform != "win32"): handleMouse()

			for event in pygame.event.get([QUIT]):
				quit = True

			if not showConsole:
				for event in pygame.event.get([KEYUP,KEYDOWN]):
					if event.type == KEYUP:
						if event.key == K_TAB: showPlayerList = False
						elif event.key == K_F9: wireframe = not wireframe
					elif event.type == KEYDOWN:
						if event.key == K_TAB: showPlayerList = True
						elif event.key == 167: showConsole = True #linux
						elif event.key == 96: showConsole = True #windows
						elif event.key == K_ESCAPE: quit = True

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
				if pressed[ord('m')]: print (mx, my)

			else:
				pressed = pygame.key.get_pressed()

				for event in pygame.event.get([KEYUP,KEYDOWN]):
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
	if len(sys.argv) > 1:
		HOST = sys.argv[1]
		if len(sys.argv) > 2:
			PORT = int(sys.argv[2])
		
		ADDR = (HOST, PORT)
	width = 800
	height = 600
	quit = False
	nick = 'Player'
	LEVEL = Level('', [])

	showPlayerList = False
	showConsole = False

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.sendto('C' + nick, ADDR)
	sock.sendto('GL', ADDR)
	sock.sendto('GKT', ADDR)

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

	try:
		time.sleep(0.1)
		while not quit:
			if (sys.platform == "win32"): handleMouse()
			render()

	except Exception, e:
		traceback.print_exc()
	finally:
		time.sleep(1)
		send("\\quit")
		sock.close()
		pygame.font.quit()
		pygame.display.quit()
#}}}
