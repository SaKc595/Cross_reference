import signal
from time import sleep

from core.owner_core import OwnerCore
from core.server_core import ServerCore
from cross_reference.cross_reference_manager import CrossReferenceManager
my_p2p_server_outer = None
my_p2p_server_inner = None

def signal_handler(signal, frame):
	shutdown_server()

def shutdown_server():
	global my_p2p_server_outer
	my_p2p_server_outer.shutdown()
	global my_p2p_server_inner
	my_p2p_server_inner.shutdown()

def main():
	count = 0
	crossref = CrossReferenceManager()
	signal.signal(signal.SIGINT, signal_handler)
	global my_p2p_server_inner
	my_p2p_server_inner = ServerCore(50087) # note
	my_p2p_server_inner.start(crm = crossref)
	my_p2p_server_inner.join_network() 

	global my_p2p_server_outer
	# my_p2p_server_outer = OwnerCore(50085, '10.84.247.68',50080) # Dtop
	# my_p2p_server_outer = OwnerCore(50090, '10.84.247.69',50080) # note
	my_p2p_server_outer = OwnerCore(50090, '192.168.0.142',50080) # note
	my_p2p_server_outer.start(crm = crossref)
	my_p2p_server_outer.join_DMnetwork()

	print("60min後にCross_reference開始(whileloop)")
	sleep(60)
	
	while True:
		print(count) 
		if 1000 < count:
			print("sleep(60)") 
			sleep(60)
			print("!!BREAK!!(1000回終了)")
			break
		my_p2p_server_outer.request_cross_reference() #クロスリファレンス開始
		count += 1
		print("=== 履歴交差回数 === :",count)
		print("次の履歴交差までsleep(60)") 
		sleep(60)
	

if __name__ == '__main__':
	main()
