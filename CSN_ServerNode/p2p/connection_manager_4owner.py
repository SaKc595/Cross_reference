import socket
import threading
import pickle
import codecs
import json
import binascii
import os

from concurrent.futures import ThreadPoolExecutor
from websocket_server import WebsocketServer
from websocket import create_connection
import time

from .owner_node_list import OwnerCoreNodeList
from .message_manager import (
	MessageManager,
	MSG_ADD_AS_OWNER,
	MSG_REMOVE_AS_OWNER,
	MSG_OWNER_LIST,
	MSG_REQUEST_OWNER_LIST,
	MSG_PING,
	ERR_PROTOCOL_UNMATCH,
	ERR_VERSION_UNMATCH,
	OK_WITH_PAYLOAD,
	OK_WITHOUT_PAYLOAD,

)
from time import sleep

# 動作確認用の値。本来は30分(1800)くらいがいいのでは
PING_INTERVAL = 10
TIME_OUT = 60


class ConnectionManager4Owner:

	def __init__(self, host,  my_port, callback, sc_self=None ):
		print('Initializing ConnectionManager...')#####
		self.host = host
		self.port = my_port
		self.my_o_host = None
		self.my_o_port = None
		self.owner_node_set = OwnerCoreNodeList()
		self.last_ping = {}	##
		self.__add_peer((host, my_port))
		self.mm = MessageManager()
		self.callback = callback
		self.my_host = self.__get_myip()##
		self.ws = WebsocketServer(port = my_port, host = self.my_host)##
		
		self.sc_self = sc_self ##
		self.flag = 0 ##


	# 待受を開始する際に呼び出される（ServerCore向け
	def start(self):

		self.ping_timer_p = threading.Timer(PING_INTERVAL, self.__check_owner_peers_connection)
		self.ping_timer_p.start()

		self.ws.set_fn_new_client(self.__new_client)##
		self.ws.set_fn_message_received(self.__ws_handle)##

		t = threading.Thread(target=self.ws.run_forever)
		t.start()

	def __ws_handle(self, client, server, message):##
		self.__handle_message((client, client['address'], message), server)
		return
	
	def __new_client(self, client, server):##
		print("%s is connected" %(client))
	
	
	# ユーザが指定した既知のCoreノードへの接続（ServerCore向け
	def join_DMnetwork(self, host, port):
		self.my_o_host = host
		self.my_o_port = port
		self.__connect_to_CROSSP2PNW(host, port)


	def get_message_text(self, msg_type, payload = None):
		"""
		指定したメッセージ種別のプロトコルメッセージを作成して返却する

		params:
			msg_type : 作成したいメッセージの種別をMessageManagerの規定に従い指定
			payload : メッセージにデータを格納したい場合に指定する

		return:
			msgtxt : MessageManagerのbuild_messageによって生成されたJSON形式のメッセージ
		"""
		msgtxt = self.mm.build(msg_type, self.port, payload)
		print('generated_msg:', msgtxt  + str("省略中"))

		return msgtxt


	# 指定されたノードに対してメッセージを送信する
	def send_msg(self, peer, msg):
		try:
			ws4edge = create_connection("ws://" + str(peer[0]) + ":" + str(peer[1]))
			ws4edge.send(msg.encode())
			ws4edge.close()

		except OSError:
			print('Connection failed for peer : ', peer)
			self.__remove_peer(peer)

	# Coreノードリストに登録されている全てのノードに対して同じメッセージをブロードキャストする
	def send_msg_to_all_owner_peer(self, msg):
		print('send_msg_to_all_owner_peer was called!')
		current_list = self.owner_node_set.get_list()
		for peer in current_list:
			if peer != (self.host, self.port):
				print("message will be sent to ... ", peer)
				self.send_msg(peer, msg)

	# 終了前の処理としてソケットを閉じる
	def connection_close(self):
		pass
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((self.host, self.port))
		self.socket.close()
		s.close()
		self.ping_timer_p.cancel()
		#離脱要求の送信
		if self.my_o_host is not None:
			msg = self.mm.build(MSG_REMOVE_AS_OWNER, self.port)
			self.send_msg((self.my_o_host, self.my_o_port), msg)


	def __connect_to_CROSSP2PNW(self, host, port):
		msg = self.mm.build(MSG_ADD_AS_OWNER, self.port)
		self.send_msg((host, port), msg)


	def __wait_for_access(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.bind((self.host, self.port))
		self.socket.listen(0)

		executor = ThreadPoolExecutor(max_workers=10)

		while True:

			print('Waiting for the connection ...')
			soc, addr = self.socket.accept()
			print('Connected by .. ', addr)
			data_sum = ''

			params = (soc, addr, data_sum)
			executor.submit(self.__handle_message, params)

	def __is_in_owner_set(self, peer):
		"""
		与えられたnodeがOwnerノードのリストに含まれているか？をチェックする

			param:
				peer : IPアドレスとポート番号のタプル
			return:
				True or False
		"""
		return self.owner_node_set.has_this_peer(peer)



	# 受信したメッセージを確認して、内容に応じた処理を行う。クラスの外からは利用しない想定
	def __handle_message(self, params ,server):#

		soc, addr, data_sum = params

		#Parse
		result, reason, cmd, peer_port, payload = self.mm.parse(data_sum)
		print("result, reason, cmd, peer_port, payload")

		status = (result, reason)

		if status == ('error', ERR_PROTOCOL_UNMATCH):
			print('Error: Protocol name is not matched')
			return
		elif status == ('error', ERR_VERSION_UNMATCH):
			print('Error: Protocol version is not matched')
			return

		elif status == ('ok', OK_WITHOUT_PAYLOAD):
			if cmd == MSG_ADD_AS_OWNER:
				print('ADD node request was received!!')
				self.__add_peer((addr[0], peer_port))
				if(addr[0], peer_port) == (self.host, self.port):
					return
				else:
					cl = pickle.dumps(self.owner_node_set.get_list(), 0).decode()
					msg = self.mm.build(MSG_OWNER_LIST, self.port, cl)
					self.send_msg_to_all_owner_peer(msg)

			elif cmd == MSG_REMOVE_AS_OWNER:
				print('REMOVE request was received!! from', addr[0], peer_port)
				self.__remove_peer((addr[0], peer_port))
				cl = pickle.dumps(self.owner_node_set.get_list(), 0).decode()
				msg = self.mm.build(MSG_OWNER_LIST, self.port, cl)
				self.send_msg_to_all_owner_peer(msg)

			##----PING
			elif cmd == MSG_PING:##
				# 特にやること思いつかない
				peer = (addr[0], peer_port)
				if ( self.__is_in_edge_set(peer) ):
					self.edge_node_set.ping_recv(peer)
				print('----------------PING receive!!------------')
				#print('List for Core nodes was requested!!')
				cl = pickle.dumps(self.core_node_set.get_list(), 0).decode()
				msg = self.mm.build(MSG_OWNER_LIST, self.port, cl)
				server.send_message(soc, msg.encode('utf-8'))
				print("core node list sent")
				return

			elif cmd == MSG_REQUEST_OWNER_LIST:
				print('List for Core nodes was requested!!')
				cl = pickle.dumps(self.owner_node_set.get_list(), 0).decode()
				msg = self.mm.build(MSG_OWNER_LIST, self.port, cl)
				self.send_msg((addr[0], peer_port), msg)


			else:
				is_owner = self.__is_in_owner_set((addr[0], peer_port))
				self.callback((result, reason, cmd, peer_port, payload), is_owner, (addr[0], peer_port))
				return


		elif status == ('ok', OK_WITH_PAYLOAD):
			if cmd == MSG_OWNER_LIST:
					# TODO: 受信したリストをただ上書きしてしまうのは本来セキュリティ的には宜しくない。
					# 信頼できるノードの鍵とかをセットしとく必要があるかも
					# このあたりの議論については６章にて補足予定
					print('Refresh the owner node list...')
					new_owner_set = pickle.loads(payload.encode('utf8'))
					print('latest owner node list: ', new_owner_set)
					self.owner_node_set.overwrite(new_owner_set)

			else:
				is_owner = self.__is_in_owner_set((addr[0], peer_port))
				self.callback((result, reason, cmd, peer_port, payload), is_owner, (addr[0], peer_port))
				return
		else:
			print('Unexpected status', status)

	def __add_peer(self, peer):
		"""
		Ownerノードをリストに追加する。クラスの外からは利用しない想定

		param:
			peer : Coreノードとして格納されるノードの接続情報（IPアドレスとポート番号）
		"""
		self.owner_node_set.add((peer))

	def __remove_peer(self, peer):
		"""
		離脱したと判断されるCoreノードをリストから削除する。クラスの外からは利用しない想定

		param:
			peer : 削除するノードの接続先情報（IPアドレスとポート番号）
		"""
		self.owner_node_set.remove(peer)


	def __check_owner_peers_connection(self):
		"""
		接続されているCoreノード全ての生存確認を行う。クラスの外からは利用しない想定
		この確認処理は定期的に実行される
		"""
		print('check_owner_peers_connection was called')
		current_owner_list = self.owner_node_set.get_list()
		changed = False
		dead_o_node_set = list(filter(lambda p: not self.__is_alive(p), current_owner_list))
		if dead_o_node_set:
			changed = True
			print('Removing owner peer', dead_o_node_set)
			current_owner_list = current_owner_list - set(dead_o_node_set)

		current_owner_list = self.owner_node_set.get_list()
		print('current owner node list:', current_owner_list)
		# 変更があった時だけブロードキャストで通知する
		if changed:
			cl = pickle.dumps(current_owner_list, 0).decode()
			msg = self.mm.build(MSG_OWNER_LIST, self.port, cl)
			self.send_msg_to_all_owner_peer(msg)
		self.ping_timer_p = threading.Timer(PING_INTERVAL, self.__check_owner_peers_connection)
		self.ping_timer_p.start()



	def __is_alive(self, target):
		"""
		有効ノード確認メッセージの送信

		param:
			target : 有効ノード確認メッセージの送り先となるノードの接続情報（IPアドレスとポート番号）
		"""
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((target))
			msg_type = MSG_PING
			msg = self.mm.build(msg_type)
			s.sendall(msg.encode('utf-8'))
			s.close()
			return True
		except OSError:
			return False

	def __get_myip(self):
	##
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		return s.getsockname()[0]

