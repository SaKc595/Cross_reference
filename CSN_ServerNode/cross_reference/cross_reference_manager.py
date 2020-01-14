import time
import socket, threading, json
import copy
import pickle
import base64
import zipfile
import os
from time import sleep
import random
import hashlib

from signature.generate_sigunature import DigitalSignature
from signature.generate_sigunature import CheckDigitalSignature
from p2p.connection_manager_4owner import ConnectionManager4Owner
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
# from p2p.owner_node_list import OwnerCoreNodeList



class CrossReferenceManager:

	def __init__(self):

		self.gs = DigitalSignature()
		self.cross_reference = []
		self.previous_cross_sig = []
		self.reference = []
		self.lock = threading.Lock()


	def set_new_cross_reference(self, cross):
		with self.lock:
			self.reference.append(cross)
			print(type(self.reference))
			print("set_new_cross_reference")


	def clear_my_reference(self, index):
		with self.lock:
			new_reference = self.reference
			del new_reference[0:index]
			print('transaction is now refreshed ... ', new_reference)
			self.reference = new_reference
		
	def add_cross_reference(self, cross): #reference部形成リスト
		self.cross_reference.append(cross)
	
	def get_reference_pool(self):
		if len(self.reference) > 0:
			return self.reference
		else:
			print("Currently, it seems cross pool is empty...")
			return []
		
	def hysteresis_sig(self):
		Current_C = self.cross_reference
		print(Current_C)
		Current_C.append(self._previous_cross_sig())
		print(Current_C)
		msg = json.dumps(Current_C)
		msg_pub = self.gs.add_public_key(msg)
		return msg_pub



	def _previous_cross_sig(self): # 更新
		# l = 
		return 

	# def cross
