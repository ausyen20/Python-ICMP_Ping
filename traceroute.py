#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#The code should measure and print the delay of a echo request for 4 times
#In addition, with the traceroute 

import socket
import os
import sys
import struct
import time
import select
import binascii
import statistics

PACKET_ID = os.getpid() & 0xFFFF
ICMP_ECHO_REQUEST = 8 #ICMP type code for echo request messages
ICMP_ECHO_REPLY = 0 #ICMP type code for echo reply messages
ICMP_CODE = socket.getprotobyname('icmp')
MAX_HOPS = 60
TIMEOUT = 10.0
MAX_PINGS = 3


def create_packet(id):
	"""Create a new echo request packet based on the given "id"."""
	# Header is type (8), code (8), checksum (16), id (16), sequence (16)
	header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, 0, id, 1)
	bytesInDouble = struct.calcsize("d")
	data = (192 - bytesInDouble) * b"Q"
	data = struct.pack("d", time.time()) + data #The time when packet is constructed will be saved internall with the packet.
	# data = 192 * b'Q'
	# Calculate the checksum on the data and the dummy header.
	my_checksum = checksum(header + data)
	#make up a new header with the actual value
	header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0,
						 socket.htons(my_checksum), id, 1)
	return header + data

#checksum method, use in ICMP header
def checksum(string): 
	csum = 0
	countTo = (len(string) // 2) * 2  
	count = 0

	while count < countTo:
		thisVal = string[count+1]* 256 + string[count]
		csum = csum + thisVal 
		csum = csum & 0xffffffff  
		count = count + 2
	
	if countTo < len(string):
		csum = csum + string[len(string) - 1]
		csum = csum & 0xffffffff 
	
	csum = (csum >> 16) + (csum & 0xffff)
	csum = csum + (csum >> 16)
	answer = ~csum 
	answer = answer & 0xffff 
	answer = answer >> 8 | (answer << 8 & 0xff00)

	#answer = socket.htons(answer)

	return answer



def receiveOnePing(icmpSocket, destinationAddress, ID, timeout):
	timeLeft = timeout
	while True:
		startedSelect = time.time()
		ready = select.select([icmpSocket], [], [], timeLeft)
		howLongInSelect = (time.time() - startedSelect)

		if ready[0] == []: #timeout handle if icmp socket not received
			return
		
		timeReceived = time.time()
		recPacket, addr = icmpSocket.recvfrom(1024)
		icmpHeader = recPacket[20:28]

		#Get the packet ID when received the packet, and socket is not timeout
		type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader) 
		
		#If id matches, then unpack the payload, get the delay
		if packetID == ID:
			bytesInDouble = struct.calcsize("d")
			timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
			return timeReceived - timeSent
		
		timeLeft = timeLeft - howLongInSelect
		if timeLeft <= 0:
			return


def sendOnePing(icmpSocket, destinationAddress, ID):

	packet = create_packet(ID) # create packet 
	icmpSocket.sendto(packet, (destinationAddress,1)) # send to the designated addr


# creates the ICMP socket pass socket to sendOnePing method
def doOnePing(destinationAddress, timeout): 
	try:
		icmpSocket =socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_CODE)
	except socket.gaierror:
		print("Unable to create socket")
		sys.exit(1)

	id = os.getpid() & 0xFFFF
	sendOnePing(icmpSocket, destinationAddress, id) 
	delay = receiveOnePing(icmpSocket, destinationAddress ,id, timeout) #return the delay upon receiving the ping
	icmpSocket.close()
	return delay
	
	
def ping(host, timeout=2, count=4):

	try:
		host = socket.gethostbyname(host)
		print("Success Found: " + host)
	except socket.gaierror:
		print("Unable to find the addresss" + host)
		return

	for i in range(count):
		delay = doOnePing(host, timeout)
		if delay == None:
			failed = f'{"Failed. Timeout: "}{timeout}{"seconds"}'
			print(failed)
		else:
			delay = round(delay*1000, 4)
			success = "Get ping in: "
			send = f'{"ID: "}{i}{", Ping: "}{delay}{" ms"}'
			print(send)
	
	print("pinging finish")

delays = [] # array for holding delays of 3 pings of each TTL, clear after every 3 pings
total_delays = [] #array for holding all delays throughout
total_seqs = 0 #use for recording total packets transmit
# This method is called for CW 1.2, traceroute 
def trace_route(host):
	timeLeft = TIMEOUT 

	for ttl in range(1, MAX_HOPS):
		for pings in range (MAX_PINGS):
			destAddr = socket.gethostbyname(host)
			icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_CODE)
			icmpSocket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))
			icmpSocket.settimeout(TIMEOUT) #Setting timeout 
			try:
				packet = create_packet(PACKET_ID)
				icmpSocket.sendto(packet, (destAddr, 0))
				sTime = time.time() #Use this start time to determine delay from nodes
				started_Select = time.time()

				#If timeLeft is negative or less than 0, end program, since no more time to process
				if timeLeft <= 0: 
					print("Request Time Out, time left below 0")
					continue

				isReady = select.select([icmpSocket], [], [], timeLeft)
				howlonginselect = (time.time() - started_Select) 

				if isReady[0] == []: #Timeout if nothing receieved
					print("Request Time Out, nothing received (icmp socket reading is empty)" ) 
					continue
				
				recvPacket, addr = icmpSocket.recvfrom(1024)
				time_Received = time.time()
				timeLeft = timeLeft - howlonginselect

			except socket.timeout:
				continue

			else:
				icmpHeader = recvPacket[20:28]
				request_type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)
				# Each type request will print latency and details regarding in reaching their desinated node
				if request_type == 11:
					bytesInDouble = struct.calcsize("d")
					time_Sent = struct.unpack("d", recvPacket[28:28 + bytesInDouble])[0]
					delay = (time_Received - sTime)*1000
					print("TLL: %d RTT: %.3f ms , Address: %s" % (ttl, delay, addr[0]))
					seq_num = 0 #Determine how many packets were transmitted

					if delay <= 0 or delay == 0 or not delay:
						delay = delay
					else:
						delays.append(delay)
						total_delays.append(delay)
					
					seq_num += pings+1 #Increment by one when a packet is transmitted
					# all pings are sent and came back, calculate the average delay, display packet loss
					if pings == 2:
						avg = round(statistics.mean(delays), 3)
						#Calculate the average delay for each TTL
						print(f'{"Average Delay of 3 pings of TTL:"}{ttl}{" --> "}{avg} {"ms"}')
						#Display the amount of packet sent, received, and percetnage of packet loss during each TTL
						print("{} packets transmitted, {} packets received, {}% packet loss\n".format(seq_num, len(delays), round((seq_num-len(delays))/ seq_num * 100),1))
						#Keep counts on numbers of packets delivered
						global total_seqs
						total_seqs = total_seqs + (pings+1)
						#Clear array for delay estimations
						delays.clear()
					
				#Request type 3 is called, when the destination is unreachable.
				elif request_type == 3:
					bytesInDouble = struct.calcsize("d")
					time_Sent = struct.unpack("d", recvPacket[28:28 + bytesInDouble])[0]
					print("Destination Unreachable, TLL %d rrt: %.0f ms , Addrees: %s" % ( ttl, (time_Received - sTime)*1000, addr[0]))
					#Reqest type 0 is called when the ping reaches the destination
					return

				elif request_type == 0:
					bytesInDouble = struct.calcsize("d")
					time_Sent = struct.unpack("d", recvPacket[28:28 + bytesInDouble])[0]
					print("Destination Reached Desintation, TTL %d RTT: %.3f ms , Address: %s" % ( ttl, (time_Received - time_Sent)*1000, addr[0]))
					#Total packets deliver, receive, and percentage of packet loss
					print("Total {} packets transmitted, Total {} packets received, {}% packet loss".format(total_seqs, len(total_delays), round((total_seqs-len(total_delays))/ total_seqs * 100),1))
					#Latency max, min, average
					print(f'{"Max Latency: "}{round(max(total_delays), 3)}{"ms, Min Latency: "}{round(min(total_delays), 3)}{"ms, Average Latency: "}{round(statistics.mean(total_delays), 3)}{"ms"}' )
					return

				else:
					#If there were other request type, then print 'Error' in terminal
					print("Error")
					break

			finally:
				icmpSocket.close()

if __name__ == '__main__':
	#Trace route
	trace_route("caida.org")
	#ICMP ping
	#ping("bbc.co.uk")