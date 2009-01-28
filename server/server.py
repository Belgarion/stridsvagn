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
#}}}
class Level: #{{{
	def __init__(self, filename):
		#self.data = read(filename)
		self.data = [[' ', '*', '*'], ['O', 'P', ' '], [' ', ' ', ' '], ['O', 'O', 'O']]
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
	def getInfo(self):
		return (self.id, self.name, self.ping, self.position, self.angle, self.towerAngle)
#}}}
class Shot: #{{{
	def __init__(self, position, angle):
		self.x = float(position[0])
		self.y = float(position[1])
		self.angle = angle
		self.speed = 1.5
		self.lastmove = time.time()
		self.erase = False
	def getInfo(self):
		return ((self.x, self.y), self.angle)
	def update(self):
		self.lastmove = time.time()

		self.x += math.sin(math.radians(self.angle)) * self.speed
		self.y -= math.cos(math.radians(self.angle)) * self.speed

		if self.x < -400 or self.x > 400 or self.y < -300 or self.y > 300:
			self.erase = True
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
				if time.time() - s.lastmove > 1.0/200:
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
				if player.addr != addr: continue

				if (time.time() - player.lastping) > 60:
					#client timed out
					dead_sockets.append(player)

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
							player.position = (x, y)
							player.angle = angle
							player.towerAngle = towerAngle
						elif data[0] == 'S': #shoot <angle>
							angle = int(data[2:])
							SHOTS.append(Shot(player.position,angle))
						elif data[0] == 'G': #get
							if data[1] == 'L': #get level
								sock.sendto(cPickle.dumps((level.filename, level.data))+"\x00", player.addr)
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

	level = Level('lvl1')

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
