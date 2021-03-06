#!/usr/bin/env python
#{{{ Imports
import socket
import thread
import sys
import traceback
import time
import random
import cPickle
import math
from Collision import *
from Vertex2 import *
#}}}
#{{{ Globals
width = 800
height = 600
#}}}
class Level: #{{{
	def __init__(self, filename):
		f = open(filename)
		d = f.read()
		e = d.split("\n")
		objs = []
		for i in range(len(e)):
			for j in range(len(e[i])):
				if e[i][j] != ' ':
					objs.append( {'position': ((j+0.5)*10-width/2, height/2-(i-0.5)*10 -10), 'type': e[i][j]} )
		self.data = objs
		f.close()
		self.filename = filename
#}}}
class Player: #{{{
	def __init__(self, addr, id):
		self.addr = addr
		self.id = id
		self.position = (0,0)
		self.angle = 0
		self.towerAngle = 0
		self.name = "Player (%d)" % id
		self.ping = 0
		self.lastping = time.time()
		self.pingpong = (0,time.time())
		self.error = (0, '')
		self.color = (random.random(), random.random(), random.random())
		self.hp = 100
	def getInfo(self):
		info = {'id': self.id, 'name': self.name, 'ping': self.ping, 'position': self.position, 'angle': self.angle, 'towerAngle': self.towerAngle, 'color': self.color}
		return info
	def kill(self):
		self.spawn()
	def spawn(self):
		newx = random.randint(-width/2 + 50, width/2 - 50)
		newy = random.randint(-height/2 + 50, height/2 - 50)
		self.position = newx, newy
		send_data(self.addr, 'FU' + cPickle.dumps(self.position))
		self.hp = 100
#}}}
class Shot: #{{{
	def __init__(self, position, angle, color, ownerId):
		self.x = float(position[0])
		self.y = float(position[1])
		self.angle = angle
		self.speed = 5
		self.lastmove = time.time()
		self.erase = False
		self.color = color
		self.size = 1.0
		self.ownerId = ownerId
	def getInfo(self):
		info = {'position': (self.x, self.y), 'angle': self.angle, 'color': self.color}
		return info
	def update(self):
		self.lastmove = time.time()

		self.x += math.sin(math.radians(self.angle)) * self.speed
		self.y -= math.cos(math.radians(self.angle)) * self.speed

		if self.x < -400 or self.x > 400 or self.y < -300 or self.y > 300 or self.checkCollision():
			self.erase = True

	def intersects(self, (x, y), angle, length, width):
		pos = Vertex2(x, y)
		selfpos = Vertex2(self.x, self.y)

		dist = pos - selfpos
		distance = math.sqrt((dist.x * dist.x) + (dist.y * dist.y))

		size = length
		if (width > size): size = width
		if distance < size + self.size/2 + 0.5:
			a = [pos, math.radians(float(angle)), Vertex2(length, width)]
			b = [selfpos, math.radians(0.0), Vertex2(self.size, self.size)]
			collision = Intersect(a,b)
			if (collision): return True
	def checkCollision(self):
		global PLAYERS
		for p in PLAYERS:
			if p.id == self.ownerId: continue
			if (self.intersects(p.position, p.angle, 21.0, 10.5)): 
				p.hp -= 50
				if (p.hp <= 0):
					p.kill()
				return True

		for obj in level.data:
			if (self.intersects(obj['position'], 0.0, 5.0, 5.0)): return True
#}}}
def send_data(addr, message): #{{{
	try:
		sock.sendto(message + "\x00", addr)
	except:
		if debug: traceback.print_exec()
#}}}
def broadcast_data(addr, message): #{{{
	global PLAYERS

	#threadlock.acquire()
	try:
		for player in PLAYERS:
			if player.addr != addr:
				sock.sendto(message + "\x00", player.addr)
	except:
		if debug: traceback.print_exc()
	#finally:
	#	threadlock.release()
#}}}
def process_connection(): #{{{
	global PLAYERS, SHOTS, RECV_BUFFER, sock

	try:
		pid = 0
		while 1:
			recvd = ''
			time.sleep(0.001)
			threadlock.acquire()
			#print "acquired lock ...",

			for s in SHOTS:
				if time.time() - s.lastmove > 1.0/30:
					if s.erase:
						SHOTS.remove(s)
					else:
						s.update()

			try:
				recvd,addr = sock.recvfrom(RECV_BUFFER)
				if len(recvd) == 0: continue
				if recvd[0] == 'C':
					print "PID: %d" % pid
					PLAYERS.append(Player(addr, pid))
					sock.sendto("I" + str(pid), addr)
					pid += 1
					print "Client (%s, %s) connected" % addr
					broadcast_data(addr, "SClient (%s, %s) connected" % addr)
			except Exception, e:
				if e[0] != 11:
					if debug: traceback.print_exc()
			
			dead_sockets = []


			PL = []
			for p in PLAYERS:
				PL.append(p.getInfo())

			try:
				broadcast_data(None, 'GPA' + cPickle.dumps(PL))
			except:
				if debug: traceback.print_exc()


			SH = []
			for s in SHOTS:
				SH.append(s.getInfo())

			try:
				broadcast_data(None, 'GPS' + cPickle.dumps(SH))
			except:
				if debug: traceback.print_exc()


			for player in PLAYERS:
				if (time.time() - p.lastping) > 60:
					#client timed out
					dead_sockets.append(p)
					
				if player.addr != addr: continue

				if (time.time() - player.lastping) > 5:
					print time.time(), ": Sending ping to", player.name
					player.lastping = time.time()
					player.pingpong = ( int(random.random()*100000), time.time() )
					try:
						sock.sendto("P%d\x00"%player.pingpong[0], addr)
					except:
						if debug: traceback.print_exc()
						player.error = sys.exc_info()[1]
						dead_sockets.append(player)
						continue



				try:
					for data in recvd.split("\x00"):
						if len(data) == 0:
							continue

						quit = 0
						if data[0] == 'C':
							pass
						elif data[0] == 'Q': #client quitting
							quit = 1
						elif data[0] == 'P': #pong
							if int(data[1:]) != player.pingpong[0]: 
								sock.sendto('wrong ping reply (' + data[1:] + ') should be ' + str(player.pingpong[0]) + '\x00', player.addr)
								#quit = 1
							else:
								player.ping = int((time.time() - player.pingpong[1])*1000)
								#print player.ping
						elif data[0] == 'M': #move <x> <y> <angle> <towerAngle>
							(x, y, angle, towerAngle) = data[2:].split(' ')
							x = float(x)
							y = float(y)
							if x < -(width/2) or x > width/2 or y < -(height/2) or y > height/2:
								pass
							else:
								player.position = (x, y)
								player.angle = angle
								player.towerAngle = towerAngle
						elif data[0] == 'S': #shoot <angle>
							angle = int(data[2:])
							SHOTS.append(Shot(player.position,angle, player.color, player.id))
						elif data[0] == 'G': #get
							if data[1] == 'L': #get level
								sock.sendto("L" + cPickle.dumps((level.filename, level.data))+"\x00", player.addr)
						elif data[0] == '\\':
							(command, sep, args) = data[1:].partition(' ')
							if command == 'quit':
								quit = 1
							elif command == 'name':
								if args.strip() != '':
									player.name = args.strip()
							elif command == 'say':
								broadcast_data(player.addr, "C"+player.name+" says "+args)
							elif command == 'players':
								pl = "Id    Player    Ping"
								for p in PLAYERS:
									pl += "\n" + str(p.id) + "    " + p.name + "   " + str(p.ping)

								sock.sendto("S" + pl+"\x00", player.addr)
								print command
						else:
							print data
							sock.sendto('echoed:' + data + "\x00", addr)

						if quit == 1:
							dead_sockets.append(player)

				except Exception, e:
					if e[0] != 11:
						if debug: traceback.print_exc()
						socket_errorcode = sys.exc_value[0]
						if socket_errorcode == 10054: #connection reset by peer
							dead_sockets.append(player)

			for player in dead_sockets:
				broadcast_data(player.addr, "S%s quits (%s)" % (player.name, player.error[1]))
				print "%s quits (%s)" % (player.name, player.error[1])
				try:
					PLAYERS.remove(player)
				except:
					traceback.print_exc()

			threadlock.release()
			#print "released lock"


	except:
		traceback.print_exc()
#}}}
if __name__ == '__main__': #{{{
	PLAYERS = []
	SHOTS = []
	HOST = ''
	PORT = 30000
	RECV_BUFFER = 65535
	ADDR = (HOST, PORT)

	debug = False
	debug = True

	level = Level('levels/1')

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(ADDR)
	sock.setblocking(0)

	threadlock = thread.allocate_lock()

	thread.start_new_thread(process_connection, ())

	try:
		while 1:
			str = raw_input()
			if (str == 'q'):
				break
	except:
		traceback.print_exc()
	finally:
		sock.close()
#}}}
