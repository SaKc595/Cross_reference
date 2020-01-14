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
from p2p.owner_node_list import OwnerCoreNodeList
from p2p.message_manager import (
	MSG_NEW_TRANSACTION,
	MSG_NEW_BLOCK,
	MSG_REQUEST_FULL_CHAIN,
	RSP_FULL_CHAIN,
	MSG_ENHANCED,
	MSG_REQUEST_CROSS_REFERENCE,
	MSG_ACCEPT_CROSS_REFFERENCE,
	MSG_CROSS_REFFERENCE,
	START_CROSS_REFFERENCE,
	COMPLETE_CROSS_REFERENCE

)
from cross_reference.cross_reference_manager import CrossReferenceManager

STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_NETWORK = 2
STATE_SHUTTING_DOWN = 3

# TransactionPoolの確認頻度
# 動作チェック用に数字小さくしてるけど、600(10分)くらいはあって良さそ
CHECK_INTERVAL = 10

class OwnerCore(object):

	def __init__(self, my_port = 50082, owner_node_host=None, owner_node_port=None  ):
		self.server_state = STATE_INIT
		print('Initializing owner server...')
		self.my_ip = self.__get_myip()
		print('Server IP address is set to ... ', self.my_ip)
		self.my_port = my_port
		self.cm = ConnectionManager4Owner(self.my_ip, self.my_port, self.__handle_message, self )
		self.mpmh = MyProtocolMessageHandler()
		self.owner_node_host = owner_node_host
		self.owner_node_port = owner_node_port
		self.gs = DigitalSignature()

		self.AC = 0
		self.Accept_list = None #Accept Count
		self.Ccount = 0 
		self.Send_list = None
		# self.previous_cross_sig = []
		

	def start(self, crm = None):
		self.server_state = STATE_STANDBY
		self.cm.start()	
		self.crm = crm

	def join_DMnetwork(self):
		if self.owner_node_host != None:
			self.server_state = STATE_CONNECTED_TO_NETWORK # 状態：親ノードへ接続中
			self.cm.join_DMnetwork(self.owner_node_host, self.owner_node_port)
		else:
			print('This server is running as Genesis Core Node...')

	def shutdown(self):
		self.server_state = STATE_SHUTTING_DOWN # 状態：切断中
		print('Shutdown server...')
		self.cm.connection_close()

	def get_my_current_state(self):
		return self.server_state

	def request_cross_reference(self):
		print("start_request_cross_reference")
		new_message = self.cm.get_message_text(MSG_REQUEST_CROSS_REFERENCE)
		self.cm.send_msg_to_all_owner_peer(new_message)

	def start_cross_reference(self):
		print("start_request_crose_reference")
		block_hash = str(random.randint(1000, 10000))
		block_msg = {}
		block_msg["block"] = block_hash
		new_message = self.cm.get_message_text(MSG_CROSS_REFFERENCE, json.dumps(block_msg, sort_keys = True ,ensure_ascii = False))
		print("new_message",new_message)
		self.cm.send_msg_to_all_owner_peer(new_message)
		# block_hash = hashlib.sha256(block)
		block_in = self._get_hash_sha256(block_hash)
		self.crm.add_cross_reference(block_in)
		print("==================== start_request_crose_reference ====================")

	def culent_crossref(self, msg):
		cross_re = json.loads(msg)
		cross_ref = cross_re["block"]
		block_in = self._get_hash_sha256(cross_ref) # hash_syori 
		self.crm.add_cross_reference(block_in)
			# self.Ccount += 1
			# J = msg[3]
			# a = int(j)
			# print(a)
			# Culent_list.remove(a)
			#Culent_list -=1 #複数nodeの場合要処理必要
	
	def cross_sig(self, cre):
		print("cross_sig")
		cross_sig = self.gs.add_public_key(cre)
		return cross_sig

	def _get_hash_sha256(self, message):
		return hashlib.sha256(message.encode()).hexdigest()

	def complete_cross_block(self, msg):
		print("complete_cross_block()")
		print( "refresh crossre ference pool")
		new_message = self.cm.get_message_text(COMPLETE_CROSS_REFERENCE, msg)
		self.cm.send_msg_to_all_owner_peer(new_message)

	def __handle_message(self, msg, is_owner, peer=None):

		if msg[2] == MSG_REQUEST_CROSS_REFERENCE:
			print("MSG_REQUEST_CROSS_REFERENCE:")
			#履歴交差了解MSG リクエストok
			new_message = self.cm.get_message_text(MSG_ACCEPT_CROSS_REFFERENCE)
			self.cm.send_msg(peer,new_message)

		elif msg[2] == MSG_ACCEPT_CROSS_REFFERENCE: # ACCEPTを受け取ったら
			print("MSG_ACCEPT_CROSS_REFFERENCE")
			# print("self.o_list.get_length = ", self.cm.owner_node_set.get_length())
			print("self.o_list.get_list = ", self.cm.owner_node_set.get_list())

			if self.AC == 0:
				self.AC = 1
				self.Accept_list = copy.deepcopy(self.cm.owner_node_set.get_list())
				self.Accept_list.remove(peer)

			elif self.AC >= 1:
				print("self.AC >= 1")
				self.Accept_list.remove(peer)
	
			else:
				pass
				
				# Culent_list = self.cm.owner_node_set.get_list()
			
			print("======================================================",self.Accept_list)

			# 履歴交差部
			if len(self.Accept_list) == 1: #Accept Count
				print("ok-----------------------------CROSS_REFERENCE")
				print("SEND_START")
				new_message = self.cm.get_message_text(START_CROSS_REFFERENCE)
				self.cm.send_msg_to_all_owner_peer(new_message)
				# 履歴交差開始
				print("accept next履歴交差開始")
				self.start_cross_reference()


		elif msg[2] == START_CROSS_REFFERENCE:
			print("START_CROSS_REFFERENCE")
			print("履歴交差開始")
			self.start_cross_reference()

		elif msg[2] == MSG_CROSS_REFFERENCE:
			print("------------------------------------------------------------",peer) #iDの照合
			print("MSG_CROSS_REFFERENCE")
			# cross_reference部のへの追加
			print("マイニング Phase1-1")
			print("msg:", msg)
			print("pyload:", msg[4])
			# print(type(msg[4]))
			if self.Ccount == 0:
				self.Ccount = 1
				self.Send_list = copy.deepcopy(self.cm.owner_node_set.get_list())
				print("=================================================================")
				if peer in self.Send_list:
					print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$=================================================================")
					self.Send_list.remove(peer)
					self.culent_crossref(msg[4])

				else:
					pass

			elif self.Ccount >= 1:
				print("self.AC >= 1")
				if peer in self.Send_list:
					self.Send_list.remove(peer)
					self.culent_crossref(msg[4])

				else:
					pass
			
			else:
				pass


			if len(self.Send_list) == 1:
				# blockの中身が確定
				# Culent_list.clear()#複数nodeの場合要処理必要
				print("CROSS_REFERENCE_ACCEPT_ALL_NODE　全ノード受信完了")
				print("マイニング Phase1-2")

				print("start---block-build-sleep(10)")
				sleep(10)
				print("end-----block-build-sleep(10)")
				# domain内のcorenodeにも知らせる必要がある
				#print("self.previous_cross_sig",self.previous_cross_sig)
				msg = self.crm.hysteresis_sig()
				
				#sig
				# blockbuild
				self.crm.set_new_cross_reference(msg)
				self.complete_cross_block(msg)


		elif msg[2] == COMPLETE_CROSS_REFERENCE:
			print("COMPLETE_CROSS_REFERENCE")
			print("self.cross_reference", self.crm.cross_reference)
			# Re-Set
			self.AC = 1 # Reset
			self.Ccount == 1
			print ("self.AC-RESET", self.AC) #Accept Count
			print( "refresh crossre ference pool")
			# できた
			# self.previous_cross_sig #前sigの更新　
			print ("from;", peer)
			print("msg[4]",msg[4])
			
		
		#if peer != None:
			if msg[2] == MSG_REQUEST_FULL_CHAIN:
				print('Send our latest blockchain for reply to : ', peer)
				mychain = self.bm.get_my_blockchain()
				print(mychain)
				chain_data = pickle.dumps(mychain, 0).decode()
				new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
				self.cm.send_msg(peer,new_message)
		else:
			if msg[2] == MSG_NEW_TRANSACTION:
				#msg[4]の型を確認
				if isinstance(msg[4],dict):# dict
					print("for_client_msg[4]")
					# d = json.loads(msg[4]) # json.loads を使って dict に変換
					b = base64.b64decode(msg[4]['bin'].encode())	 # base64 を使ってバイナリから復元
					with open(dirname+"ZIP_busdata/accept_busdata/server_busdata.zip", "wb") as f:
						f.write(b)

					with zipfile.ZipFile(dirname+"ZIP_busdata/accept_busdata/server_busdata.zip") as zf:
						zf.extractall(dirname+"ZIP_busdata/accept_busdata")
					
					with open(dirname+"ZIP_busdata/accept_busdata/msg_pub.txt") as f:
						readdata = f.read().splitlines()
						print("read txt")
						new_transaction = json.loads(readdata[0])
				
				if isinstance(msg[4],str):# str
					print("for_server_msg[4]")
					print(type(msg[4]))
					new_transaction = json.loads(msg[4])
				
				else:
					print("object has no attribute")
					pass
				
				type(new_transaction)			

				current_transactions = self.tp.get_stored_transactions()
				if new_transaction in current_transactions:
					print("this is already pooled transaction:")
					return

				if not is_core:#from edge node
					ds = CheckDigitalSignature(new_transaction)
					CHECK_SIGNATURE = ds.get_flag()#ds.check_signature(new_transaction)
					if  CHECK_SIGNATURE == False:
						print('---------------------------------------')
						print ('DigitalSignature is False')
						print('---------------------------------------')
						return
					else:
						print('---------------------------------------')
						print ('DigitalSignature is True')
						print('---------------------------------------')

					self.tp.set_new_transaction(new_transaction)
					new_message = self.cm.get_message_text(MSG_NEW_TRANSACTION, json.dumps(new_transaction, sort_keys=True, ensure_ascii=False))
					self.cm.send_msg_to_all_peer(new_message)
				else:
					self.tp.set_new_transaction(new_transaction)

			elif msg[2] == MSG_NEW_BLOCK:

				if not is_core:
					print('block received from unknown')
					return

				# 新規ブロックを検証し、正当なものであればブロックチェーンに追加する
				new_block = json.loads(msg[4])
				print('new_block: ', new_block)
				if self.bm.is_valid_block(self.prev_block_hash, new_block):# is new block valid?
					# ブロック生成が行われていたら一旦停止してあげる（threadingなのでキレイに止まらない場合あり）
					if self.is_bb_running:
						self.flag_stop_block_build = True
					self.prev_block_hash = self.bm.get_hash(new_block)
					self.bm.set_new_block(new_block)
				else:
					#　ブロックとして不正ではないがVerifyにコケる場合は自分がorphanブロックを生成している
					#　可能性がある
					self.get_all_chains_for_resolve_conflict()

			elif msg[2] == RSP_FULL_CHAIN:

				if not is_core:
					print('blockchain received from unknown')
					return
				# ブロックチェーン送信要求に応じて返却されたブロックチェーンを検証し、有効なものか検証した上で
				# 自分の持つチェインと比較し優位な方を今後のブロックチェーンとして有効化する
				new_block_chain = pickle.loads(msg[4].encode('utf-8'))
				print(new_block_chain)
				result, pool_4_orphan_blocks = self.bm.resolve_conflicts(new_block_chain)
				print('blockchain received')
				if result is not None:
					self.prev_block_hash = result
					if len(pool_4_orphan_blocks) != 0:
						# orphanブロック群の中にあった未処理扱いになるTransactionをTransactionPoolに戻す
						new_transactions = self.bm.get_transactions_from_orphan_blocks(pool_4_orphan_blocks)
						for t in new_transactions:
							self.tp.set_new_transaction(t)
				else:
					print('Received blockchain is useless...')
				# self.main_window.set_chain(self.bm.chain)

			elif msg[2] == MSG_ENHANCED:
				# P2P Network を単なるトランスポートして使っているアプリケーションが独自拡張したメッセージはここで処理する。SimpleBitcoin としてはこの種別は使わない
				# self.mpmh.handle_message(msg[4])
				print("MSG_ENHANCED")
		
		print("owner_core__handle_message_")

	def __get_myip(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		return s.getsockname()[0]
