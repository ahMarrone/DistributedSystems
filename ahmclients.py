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
import struct
from urlparse import urlparse
from ahmprotocols import DayTimeProtocol,HTTPProtocol,TCPDataReceiver,Now
import json
import time
import rsa
import datetime
import pprint
import thread
from base64 import b64encode

	
	
	#   Estructura de clases cliente del modulo.
	#
	#                               AbstractClient
	#									|
	#									|           extend
	#				----------------------------------------------------------------------------
	#				|																			|
	#    		AbstractTCPClient		  											   AbstractUDPClient
	#               |																			|		
	#				|																			|
	#		--------------------------------------------------------------				        ----------
	#		|					|					|					 |			   					|	
	#	BasicTCPClient		BasicHTTPClient		DayTimeTCPClient   RemoteTerminalClient	         BasicUDPClient

####################################################################################################
####################################################################################################
###########         CONTIENE CLASES QUE HACEN DE CLIENTES DE DIFERENTES SERVICIOS         ######
####################################################################################################
####################################################################################################



class AbstractClient:
	
	bufferSize = 4096
	defaultData = "Saludos al servidor..."
	
	def __init__(self,host,port,sockFamily,sockType,data = None):
		self.host = host
		self.port = port
		self.sockFamily = sockFamily
		self.sockType = sockType
		if not data:
			self.clientData = self.defaultData
		else:
			self.clientData = data
		self.createSocket()
		
	def createSocket(self):
		self.socket = socket.socket(self.sockFamily, self.sockType) # Declaración del Socket
		
	# Abstracto. A implementar por sub-clases. Método que inicia las acciones del cliente (Pre-armado de datos a enviar, envio de datos, obtencion de respuesta, etc).
	def run(self):
		raise NotImplementedError()
		
	# Metodo abstracto	
	def sendData(self,data):
		raise NotImplementedError()
		
	# Metodo abstracto
	def receiveData(self,bufferSize):
		raise NotImplementedError()


class AbstractTCPClient(AbstractClient):
	
	def __init__(self,host,port,data = None):
		AbstractClient.__init__(self,host,port,socket.AF_INET, socket.SOCK_STREAM,data)
		self.connectSocket()
	
	def sendData(self,data):
		self.socket.sendall(data)
		
		
	
	def receiveSingleData(self,bufferSize): # Test
		data = self.socket.recv(bufferSize)
		return data		
	
	# Override. fuente: http://code.activestate.com/recipes/408859-socketrecv-three-ways-to-turn-it-into-recvall/
	def receiveEndData(self,bufferSize):
		total_data=[]
		while True:
			data = self.socket.recv(bufferSize)
			if not data or data == "\0":
				break
			total_data.append(data)
		return ''.join(total_data)
		
	def receiveData(self,bufferSize):
		total_data=[]
		while True:
			data = self.socket.recv(bufferSize)
			if not data:
				break
			total_data.append(data)
		return ''.join(total_data)
		
	def connectSocket(self):
		self.socket.connect((self.host, self.port))         # Inicia la conexión TCP contra el servidor
		
	
class AbstractUDPClient(AbstractClient):
	
	def __init__(self,host,port,data = None):
		AbstractClient.__init__(self,host,port,socket.AF_INET, socket.SOCK_DGRAM,data)
	
	
	def sendData(self,data):
		self.socket.sendto(data, (self.host, self.port))
		
		
	def receiveEndData(self,bufferSize):
		total_data=[]
		while True:
			data = self.socket.recvfrom(bufferSize)
			print data
			if not data or (data == "\0"):
				break
			total_data.append(data)
		return ''.join(total_data)
	
	
	def receiveSingleData(self,bufferSize):
		receive = self.socket.recvfrom(bufferSize) 
		return receive	
	
	def receiveData(self,bufferSize):
		data = ""
		receive = self.socket.recvfrom(bufferSize)
		while len(receive):
			data += receive
			receive = self.socket.recvfrom(bufferSize) 
		return data	
		
# Cliente TCP Basico
# Inicia conexion contra un servidor TCP, envia una serie de datos, e imprime por salida estandar la respuesta del servidor
class BasicTCPClient(AbstractTCPClient):
	
	def __init__(self,host,port,data = None):
		AbstractTCPClient.__init__(self,host,port,data)
		
	def run(self):
		sendData = str(raw_input("Ingrese datos a ser enviados al servidor: \n"))
		self.sendData(sendData)
		self.sendData("\0") # En esta linea envio el caracter de corte. El servidor interpreta que es el fin de envio de datos por parte del cliente.
		datos = TCPDataReceiver.receiveSingleData(self.socket,self.bufferSize) # Recibo algo
		print "Respuesta del servidor: \n" + datos
		self.socket.close()

			
# Cliente UDP Basico
# Inicia conexion contra un servidor TCP, envia una serie de datos, e imprime por salida estandar la respuesta del servidor			
class BasicUDPClient(AbstractUDPClient):
	
	def __init__(self,host,port,data = None):
		AbstractUDPClient.__init__(self,host,port,data)
		
		
	def run(self):
		print "Enviando datos desde el cliente: " + self.clientData
		self.sendData(self.clientData)
		data = self.receiveSingleData(self.bufferSize) # La respuesta
		print "Respuesta del servidor: " + data[0]
		self.socket.close()
		
		
