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

from datetime import datetime,timedelta
import pytz


### DAYTIME ###


### PDU de Aplicacion Daytime  (QUERY):


#Formato de la PDU:



#### BIT | 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 |		
#### 0   |  is_query     |       message_code    |                     
#### 16	 |  	     country_code                |
#### 32	 |           answer_count                |
#### 	 | --------------------------------------|
#### 	 |         SECCION RESPUESTA             |
#### 	 |                                       |


##	DETALLE

#	 	Campo    			|		Tamaño
#	-----------------------------------------------
#	   is_query 			|		1 byte
#      message_code			|		1 byte
#	   country_code			|		2 bytes
#	   answer_count			|		2 bytes


# is_query : Toma valor cero o uno. 1 = El mensaje es un query.
#								    0 = El mensaje es una respuesta a un query.
#
# message_code : codigo del mensaje. Puede tomar valores cero o uno. Tiene distinto significado según el mensaje sea un query o una respuesta
#				Semántica:
#					a ) Si el mensaje es un query    :   1 = Obtener respuesta de la ciudad especificada en el campo country_code  ("find_country")
#														 0 = Obtener respuesta en time zone por defecto (ubicado en defaultZone.txt)
#					b ) Si el mensaje es un request :    1 = Query correcto. Se retornan datos al cliente ("country_found")
#														 0 = Query incorrecto. El código de ciudad en incorrecto ("country_not_found")
#
# country_code : Codigo de pais de la cual se desea saber el tiempo. 
#
# answer_count : cantidad de respuestas al query recibido. (Una ciudad puede tener varios husos horarios, y se pueden obtener N respuestas)

# SECCION RESPUESTA:
#
# Cada respuessta estara formada por:
#
#
#		 	Campo    			|		Tamaño
#		Nombre Zona				|		32 bytes
#		Tiempo					|		17 bytes

# TOTAL : 49 bytes cada entrada en la respuesta !! 

# Por lo tanto:
# Cada query tendra un tamaño de 6 bytes.
# Cada respuesta tendrá un tamaño de 6 bytes, mas (49 bytes * answer_count)


class DayTimeProtocol():
	
	TIME_FORMAT = '%d/%m/%y %H:%M:%S'
	
	# Campos de la PDU
	# (byte_inicio,byte_final,tamaño_total)
	BYTES_IS_QUERY = (0,1,1)
	BYTES_MESSAGE_CODE = (1,2,1)
	BYTES_COUNTRY_CODE = (2,4,2)
	BYTES_ANSWER_COUNT = (4,6,2)
	BYTES_ANSWER_ZONE_NAME  = (6,38,32)
	BYTES_ANSWER_ZONE_TIME  = (38,55,17)
	
	# Retorna diccionario con la estructura:
	# timeZones = { Cod.Pais1 => [Nombre_Zona1,Nombre_Zona2,Nombre_ZonaN]
	#				 Cod. Pais2 => [Nombre Zona]
	#					...
	#				}
	#
	#
	@staticmethod
	def loadCountryZones(zonesFile):
		timeZones = {}
		for countryLine in zonesFile:  # CONTIENE: {Cod.Pais:[Nombre de Zona1,Nombre Zona2,...]}
			countryEntry = countryLine.split("\t")
			if countryEntry[0] in timeZones: # ya existe el pais en el diccionario. Agrego a la lista de time zones el valor
				timeZones[countryEntry[0]].append(countryEntry[1])
			else: # creo lista con el time zone
				timeZones[countryEntry[0]] = [countryEntry[1]]
		return timeZones
	
	
	# Parseo request del protocolo DayTime.
	# Retorna lista [is_query,message_code,country_code,answer_count]
	@staticmethod
	def parseRequest(request):
		result  = []
		result.append(request[DayTimeProtocol.BYTES_IS_QUERY[0]:DayTimeProtocol.BYTES_IS_QUERY[1]]) # leo primeros N bytes (2)
		result.append(request[DayTimeProtocol.BYTES_MESSAGE_CODE[0]:DayTimeProtocol.BYTES_MESSAGE_CODE[1]])
		result.append(request[DayTimeProtocol.BYTES_COUNTRY_CODE[0]:DayTimeProtocol.BYTES_COUNTRY_CODE[1]])
		result.append(request[DayTimeProtocol.BYTES_ANSWER_COUNT[0]:DayTimeProtocol.BYTES_ANSWER_COUNT[1]])
		return result
		
	# Parseo response del protocolo DayTime.
	# Retorna lista [is_query,message_code,country_code,answer_count,[answer_section]]
	@staticmethod
	def parseResponse(response):
		result  = DayTimeProtocol.parseRequest(response) # obtengo primeros datos (cabeceras)
		# tengo que leer la seccion de respuestas
		answers = []
		tamanoEntrada = DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[2] + DayTimeProtocol.BYTES_ANSWER_ZONE_TIME[2]
		for index in range(int(result[3])):  # itero sobre todas las respuestas
			zoneName =  response[DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[0] + (index * tamanoEntrada) :DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[1] + (index * tamanoEntrada)]
			time =  response[DayTimeProtocol.BYTES_ANSWER_ZONE_TIME[0] + (index * tamanoEntrada) : DayTimeProtocol.BYTES_ANSWER_ZONE_TIME[1] + (index * tamanoEntrada)]
			answers.append([zoneName,time])
		result.append(answers)
		return result	
		
	@staticmethod
	def getRequestPDU(countryCode = None):
		pdu = "1"    #(is_query  = "1")  1 byte
		if countryCode:
			pdu += str(1)  #   (message_code = 1) 1 byte
			pdu += countryCode[:2]  #(seteo country_code) 2 bytes
		else:
			pdu += "0"     #(message_code = "0")
			pdu += "00"    # (country_code = "00")
		pdu += "00"    # (answer_count = 00 )
		return pdu
		
	@staticmethod
	def getResponsePDU(messageCode,answers,countryCode = None):
		pduResponse = "0"
		pduResponse += messageCode
		pduResponse += countryCode if countryCode else "00"
		pduResponse += str(len(answers)).zfill(2) # seteo a 2 bytes el campo
		for answer in answers: # contruyo seccion de respuestas al query
			pduResponse += answer[0] + answer[1]  # nombre de zona + tiempo
		return pduResponse
		
	# El request es una lista:  [is_query,message_code,country_code,answer_count]
	# Parametros:
	#	Request del cliente parseado.
	#   Diccionario con los Time Zones 
	@staticmethod
	def constructResponse(request,timeZones,defaultZone): 
		isQuery = request[0]
		messageCode = request[1]
		countryCode = request[2]
		# Si recibo un query, que busca un determinado pais, verifico que sea valido.
		responseCode = "1"
		answer = []
		if int(messageCode):
			if countryCode in timeZones:
				for countryEntry in timeZones[countryCode]: # countryEntry = [nombreZona] 
					answer.append(DayTimeProtocol.makeAnswerField(countryEntry))
			else:
				# El codigo de pais en invalido, retornar meesage_code = 0 y lista de respuestas vacia 
				responseCode = "0"
		else: # El cliente quiere obtener hora en el time zone por defecto (ubicado en el archivo defaultZone.txt)
			answer.append(DayTimeProtocol.makeAnswerField(defaultZone))
		return DayTimeProtocol.getResponsePDU(responseCode,answer,countryCode)
		
	
	@staticmethod
	def makeAnswerField(zoneName):
		utcDate = datetime.utcnow()
		utcDate = utcDate.replace(tzinfo=pytz.utc)
		time = datetime.astimezone(utcDate, pytz.timezone(zoneName))
		time = datetime.strftime(time,DayTimeProtocol.TIME_FORMAT)
		'''if not deltaTime:
			time = datetime.strftime(datetime.utcnow(),DayTimeProtocol.TIME_FORMAT)
		else:
			timeObject = datetime.utcnow()  + timedelta(hours = deltaTime)
			time =  datetime.strftime(timeObject,DayTimeProtocol.TIME_FORMAT)
		if len(zoneName) > DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[2]:
			zoneName[:DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[2]]'''
		return [zoneName.ljust(DayTimeProtocol.BYTES_ANSWER_ZONE_NAME[2]),time]
	
	
	'''@staticmethod	
	def getUTCBaseAnswer():
		zoneName = "UTC+0"
		answer = DayTimeProtocol.makeAnswerField(zoneName)
		return answer'''
		
		
		
		
class HTTPProtocol:
	
	# La peticion tiene tres partes:
	#	Request-Line:
	#		Metodo \s URI \s HTTPVersion \r\n
	#	Headers:
	#		headerKey: \s headerValue \r\n
	#		...
	#   \r\n
	#	Body Opcional
	@staticmethod
	def createRequest(host,port,headers,method,resource,httpVersion):
		#request = method + " http://" + host + ":" + str(port) + resource + " " +  httpVersion + "\r\n"
		request = method + " " + resource + " " +  httpVersion + "\r\n"
		for k,v in headers.items():
			request += k + ": " + v + "\r\n"
		request += "\r\n"
		return request
		
	
	# Parse response. Etructura:
	#	
	#	- Status-Line : HTTP-Version SP Status-Code SP Reason-Phrase CRLF
	#	- Headers : headerKey: \s headerValue \r\n
	#	 ...
	#    \r\n
	#   - Cuerpo respuesta
	#
	#	Retorna lista de 3 elementos:
	#		1er elemento (Status Line) = [httpVersion,status-code,reason-phrase] (lista)
	#		2do elemento (Headers) = {header1:value1,header2,value2,...}   (diccionario)
	#		3er elemento (Response body) = responseBody (string)
	#
	#
	@staticmethod
	def parseHTTPResponse(response):
		HTTPResponseParsed = []    # lista que devolvera el metodo como resultado
		response,bodyRequest = response.split("\r\n\r\n",1)   # esta linea separa la linea de status-line y los headers de todo el cuerpo de la respuesta. Tiene dos objetos
		responseParsed = response.split("\r\n") # separo cada parte del response. El primer item es el status-line, los siguientes son los headers
		# parseo status-line
		httpVersion = responseParsed[0][:8]
		statusCode = responseParsed[0][9:12]
		reasonPhrase = responseParsed[0][13:]
		HTTPResponseParsed.append([httpVersion,statusCode,reasonPhrase])
		# parseo headers
		headers = {}
		for headerIndex in range(1,len(responseParsed) - 1):
			k,v = responseParsed[headerIndex].split(": ")
			headers[k] = v
		HTTPResponseParsed.append(headers)
		# inserto el body del response a la respuesta
		HTTPResponseParsed.append(bodyRequest)
		# Retorna response parseado
		return HTTPResponseParsed
	
	
	#
	#	Retorna lista de 3 elementos:
	#		1er elemento (Status Line) = [requestType,resource,version] (lista)
	#		2do elemento (Headers) = {header1:value1,header2,value2,...}   (diccionario)
	#		3er elemento (request body) = requestBody (string)	
	@staticmethod
	def parseHTTPRequest(request):
		HTTPrequestParsed = []    # lista que devolvera el metodo como resultado
		request,bodyRequest = request.split("\r\n\r\n",1)   # esta linea separa la linea de status-line y los headers de todo el cuerpo de la respuesta. Tiene dos objetos
		requestParsed = request.split("\r\n") # separo cada parte del request. El primer item es el status-line, los siguientes son los headers
		# parseo status-line
		statusLine =  requestParsed[0].split()
		requestType = statusLine[0]
		resource = statusLine[1]
		version = statusLine[2]
		HTTPrequestParsed.append([requestType,resource,version])
		# parseo headers
		headers = {}
		for headerIndex in range(1,len(requestParsed) - 1):
			k,v = requestParsed[headerIndex].split(": ")
			headers[k] = v
		HTTPrequestParsed.append(headers)
		# inserto el body del request a la respuesta
		HTTPrequestParsed.append(bodyRequest)
		# Retorna request parseado
		return HTTPrequestParsed
	
# Clase TCPDataReceiver
# Implementa los distintos metodos de recepcion de datos sobre un socket
class TCPDataReceiver():
	
	# receiveSingleData. Recibe un conjunto de datos menor o igual al tamño de buffer especificado)
	@staticmethod
	def receiveSingleData(socket,bufferSize):
		data = socket.recv(bufferSize)
		return data
		
	'''# receiveData. Recibe datos en un bucle, del cual se escapa cuando se reciben 0 bytes en el socket. (En TCP sucede cuando se cierra la conexion)
	@staticmethod
	def receiveData(socket,bufferSize):
		total_data=[]
		while True:
			data = socket.recv(bufferSize)
			if not data:
				break
			total_data.append(data)
		return ''.join(total_data)'''
	
	# receiveData. Recibe datos en un bucle, del cual se escapa cuando se reciben 0 bytes en el socket. (En TCP sucede cuando se cierra la conexion)
	@staticmethod
	def receiveData(socket,bufferSize):
		data = socket.recv(bufferSize)
		while len(data) == bufferSize:
			data += socket.recv(bufferSize)
		return data
	
	# receiveEndData. Recibe datos en un bucle, el cual termina cuando se recibe un o un conjunto de bytes especificados.
	@staticmethod
	def receiveEndData(socket,endExpession,bufferSize):
		total_data=[]
		while True:
			data = socket.recv(bufferSize)
			if not data or data == endExpession:
				break
			total_data.append(data)
		return ''.join(total_data)



# Protocolo Marrone Ricci Token Ring



#Formato de la PDU:



#### BIT | 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 |		
#### 0   |           nodeSource			     	 |                     
#### 16	 |  	     nodeDest	                 |
#### 32	 |           messageCode                 |
#### 	 | --------------------------------------|
#### 	 |           message	                 |
#### 	 |                                       |


# nodeSource: ID del nodo que origina el mensaje.
# nodeDest: ID del nodo destino.
# messageCode: código del mensaje. Determina el tipo de mensaje:
#				Code 00 =>  Finalizar intercambio de mensajes.
#				Code 01 =>  El nodo origen pasa el token a su vecino.
#				Code 02 =>  El nodo origen desea enviar un mensaje al nodo destino. 
#				Code 03 =>  El nodo destino, le avisa al nodo origen que su mensaje fue recibido.
# message: Mensaje (String) que envía el origen al destino (Tiene sentido cuando el código de mensaje = 2. En cualquier otro tipo de mensaje esta campo se ignora)
#


class MRTokenRingProtocol():
	
	# Campos de la PDU
	# (byte_inicio,byte_final,tamaño_total)
	BYTES_NODE_SOURCE = (0,2,2)
	BYTES_NODE_DEST = (2,4,2)
	BYTES_CODE = (4,6,2)
	BYTES_MESSAGE = (6,-1,-1) # En este caso se ignoran los dos ultimos valores. Siempre se lee hasta el final
	
	@staticmethod
	def createPDU(source,dest,code,message = ""):
		pdu = ""
		pdu += source.zfill(MRTokenRingProtocol.BYTES_NODE_SOURCE[2])
		pdu += dest.zfill(MRTokenRingProtocol.BYTES_NODE_DEST[2])
		pdu += code.zfill(MRTokenRingProtocol.BYTES_CODE[2])
		pdu += message
		return pdu
	
	
	@staticmethod
	# Crea la pdu a traves a una lista recibida
	def createPDUFromList(lista):
		return MRTokenRingProtocol.createPDU(lista["nodeSource"],lista["nodeDest"],lista["messageCode"],lista["message"])
		
	@staticmethod	
	def getFinalizePDU():
		return MRTokenRingProtocol.createPDU("00","00","00")
		
	@staticmethod	
	def getPassTokenPDU():
		return MRTokenRingProtocol.createPDU("00","00","01")
	
	@staticmethod	
	# Retorna dicc. con los campos de la PDU parseados.
	# claves => nodeSource,nodeDest,messageCode,message
	def parsePDU(pdu):
		result  = {}
		result["nodeSource"] = pdu[MRTokenRingProtocol.BYTES_NODE_SOURCE[0]:MRTokenRingProtocol.BYTES_NODE_SOURCE[1]]
		result["nodeDest"] = pdu[MRTokenRingProtocol.BYTES_NODE_DEST[0]:MRTokenRingProtocol.BYTES_NODE_DEST[1]]
		result["messageCode"] = pdu[MRTokenRingProtocol.BYTES_CODE[0]:MRTokenRingProtocol.BYTES_CODE[1]]
		result["message"] = pdu[MRTokenRingProtocol.BYTES_MESSAGE[0]:]
		return result
		
		
		
class Now:
    def __init__(self):
        self._now = None
    def get(self):
		# Retorna la fecha y hora actual en milisegundos
		self._now = datetime.now()
		return mktime(self._now.timetuple()) + self._now.microsecond/1000000.0
