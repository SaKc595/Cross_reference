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
		self.timer = 0
		self.flag = False
		self.cross_reference_flag = False
		self.inc = 0


	def set_new_cross_reference(self, cross):
		with self.lock:
			self.reference.append(cross)
			print("======= set_new_cross_ref =======")

	def clear_my_reference(self, index):
		with self.lock:
			new_reference = self.reference
			del new_reference[0:index]
			print('reference is now refreshed ... ', new_reference)
			self.reference = new_reference
		
	def add_cross_reference(self, cross): #reference部形成リスト
		self.cross_reference.append(cross)

	def clear_cross_reference(self):
		self.cross_reference.clear()
		print(" ======== reference部形成リストclear ======== ",self.cross_reference)
	
	def get_reference_pool(self):
		if len(self.reference) > 0:
			return self.reference[0]
		else:
			print("Currently, it seems cross pool is empty...")
			return []
		
	def hysteresis_sig(self):
		Current_C = self.cross_reference
		print(Current_C)
		Current_C.append(self.get_previous_cross_ref())
		print(Current_C)
		msg = json.dumps(Current_C)
		msg_pub = self.gs.add_public_key(msg)
		print("",msg)
		self.store_previous_cross_ref(msg_pub)
		return msg_pub

	def store_previous_cross_ref(self, msg_sig):

		msg_hash = self._get_hash_sha256(msg_sig)
		print("store_previous_crossref_hash")
		d = self.previous_cross_sig
		d = {
			'previous_crossref_hash' : msg_hash
		}
		self.previous_cross_sig = d.get('previous_crossref_hash')
		print("======= renew prev_crossref_hash  ... ======= ",self.previous_cross_sig)

	def _get_hash_sha256(self, message):
		return hashlib.sha256(message.encode()).hexdigest()

	def get_previous_cross_ref(self):
		print("get_previous_cross_sig")
		msg_sig = self.previous_cross_sig
		return msg_sig

	def time_start(self):
		self.flag = True
		self.timer =  time.time()
	
	def time_stop(self):
		if self.flag:
			t = time.time() - self.timer
			self.flag = False
			return t
		
		else:
			return None


	def block_cheek(self):
		self.cross_reference_flag = False
