#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  sin título.py
#  
#  Copyright 2013 Agustin <Agustin@AGUSTIN-NBK>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
import socket
import select
import ahmclients
from ahmprotocols import HTTPProtocol,DayTimeProtocol,TCPDataReceiver,MRTokenRingProtocol,Now
import json
import datetime
from urlparse import urlparse
import time
import subprocess
import os
import rsa
import threading
from base64 import b64decode



	# Arbol de las jerarquia de clases:
	#                               AbstractServer
	#									|
	#									|           extend
	#				---------------------------------------------------------------------------------------------------------
	#				|					(asociado a)																		|
	#    		AbstractTCPServer-------------------- SimpleTCPHandler 		  										AbstractUDPServer
	#               |						|																				|		
	#				|						|																				|
	#				|						|---------MultipleTCPHandler													|
	#				|																										|
	#				|																										|
	#				|																										|
	#				|																										|
	#				|																										|
	#				|																										|
	#     ---------------------------------------																---------------------
	#     |     		  |			            |			      												|					|
	#   EchoTCPServer   DayTimeTCPServer	 RemoteTerminalServer										EchoUDPServer		DayTimeUDPServer
	
	




######################################################################################################
############ COMIENZO DEFICINICION DE CLASES BASES PARA IMPLEMENTAR SERVIDORES #########################
######################################################################################################

	
	
	
class AbstractServer:   # Clase abstracta. Defino bases para implementar servidores TCP/UDP

	bufferSize = 4096
	
	
	def __init__(self,host,port,sockFamily,sockType):
		self.host = host
		self.port = port
		self.sockFamily = sockFamily
		self.sockType = sockType
		try:
			self.createSocket()
			self.initializeSocket()
			print "Socket creado (" + self.host + ":" +  str(self.port) + ")"
		except Exception as e:
			print "No se ha podido crear el socket"
			print e
		
		
	# creacion del socket y operaciones comunes entre las sub-clases
	def createSocket(self):
		self.socket = socket.socket(self.sockFamily,self.sockType)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permito reutilizar socket
		self.socket.bind((self.host,self.port))
		
	#Las sub-clases que deben realizar acciones sobre el socket del servidor, deben sobreescribir este metodo
	def initializeSocket(self):
		pass
		
	
	
	# Método abstracto. Las sub-clases deben implementarlo. Se debe escribir el bucle principal del servidor
	def run(self):
		raise NotImplementedError()



class AbstractTCPServer(AbstractServer):
	
	# Constantes de clase
	connectionsNumber = 10
	MULTIPLE = "multiple"
	SINGLE = "single"
	
	def __init__(self,host,port,handler = "single"):   # Tiene asociado un handler. SimpleTCPHandler acepta un cliente por vez. MultipleTCPHandler acepta múltiples clientes
		AbstractServer.__init__(self,host,port,socket.AF_INET, socket.SOCK_STREAM)
		if handler == AbstractTCPServer.SINGLE:
			self.handler = SimpleTCPHandler(self)
		elif handler == AbstractTCPServer.MULTIPLE:
			self.handler = MultipleTCPHandler(self)
			
		
	
	def initializeSocket(self):
		self.socket.listen(self.connectionsNumber)
	
	
		
	def acceptConnection(self):
		client_sock, client_addr = self.socket.accept() # Acepta conexiones y retorna el sock para llegar al cliente y su dirección
		print "Conexion desde:", client_sock.getpeername()
		return client_sock, client_addr	

	
	
	# Metodo que recibe datos desde el sock del cliente pasado como parametro.
	# El metodo estandar que utiliza es el metodo "receiveData" que se encuentra implementado en la clase TCPDataReceiver dentro del paquete ahmprotocols
	# Si se desea utilizar otro metodo, se debe sobreescribir el mismo en las clases hijas.
	def receiveData(self,client_sock):
		return TCPDataReceiver.receiveData(client_sock,self.bufferSize)
		
	def sendResponse(self,client_sock,data):
		client_sock.send(data)
			
	def run(self):
		while 1:
			self.handler.handleRequests()
	
		

	# Metodo abstracto a implementar por los servidores concretos. Deben definir la logica a realizar cuando un cliente les envia datos.
	def manageRequest(self,clientSock,data):
		raise NotImplementedError()
		
		
class AbstractUDPServer(AbstractServer):
	
	
	def __init__(self,host,port):
		AbstractServer.__init__(self,host,port,socket.AF_INET, socket.SOCK_DGRAM)
	
	
	def run(self):
		while True:                    # Bucle principal del servidor
			data, address = self.socket.recvfrom(self.bufferSize) # espera conexiones
			self.manageRequest(address,data)
	
	def sendResponse(self,address,data):
		self.socket.sendto(data,address)
	
	# Metodo abstract a implementar por las sub-clases. Definir la lógica a realizar cuando llega un peticion de un cliente
	def manageRequest(self,address,data):
		raise NotImplementedError()

##############################   TCP REQUEST HANDLERS  - Simple,MultiUsuario  ###################################

class SimpleTCPHandler:
	
	def __init__(self,server):
		self.server = server
		
	# Metodo que maneja las conexiones de los clientes (En este caso acepta uno solo por vez)
	def handleRequests(self):
		client_sock, client_addr = self.server.acceptConnection()
		data = self.server.receiveData(client_sock)  # recibo datos desde el sock del cliente que inicio la conexion
		self.server.manageRequest(client_sock,data)
		
		
class MultipleTCPHandler:
	
	
	connectionLists = []
	
	def __init__(self,server):
		self.server = server
		self.connectionLists.append(self.server.socket) # Agrego socket del servidor a la lista de conexiones


	# Metodo que maneja las conexiones de los clientes (En este caso acepta multiples conexiones)
	def handleRequests(self):
		readSockets,writeSockets,errorSockets = select.select(self.connectionLists,[],[])
		for sock in readSockets:
				if sock == self.server.socket:  # Recibo una nueva conexion
					client_sock, client_addr = self.server.acceptConnection()
					#print "Conexión nueva desde (%s, %s) " % client_addr
					self.connectionLists.append(client_sock)
				else:  # Recibo datos desde un cliente
					data = self.server.receiveData(sock)
					if data:
						self.server.manageRequest(sock,data)


###########              TERMINA SECCION SERVIDORES ABSTRACTOS			      ##########################

	

####################################################################################################
####################################################################################################
###########              COMIENZA SECCION SERVIDORES CONCRETOS			      ##########################
####################################################################################################
####################################################################################################
	
### ECHO SERVERS ##################################


class EchoTCPServer(AbstractTCPServer):
	
	def receiveData(self,client_sock):
		return TCPDataReceiver.receiveEndData(client_sock,"\0",self.bufferSize)
	
	
	def manageRequest(self,clientSock,data):
		self.sendResponse(clientSock,data)
		print "Respondiendo a " + client_sock.getpeername()
    
		
		
class EchoUDPServer(AbstractUDPServer):
	
	def manageRequest(self,clientSock,data):
		self.sendResponse(clientSock,data)
		


