import signal
from time import sleep

from core.owner_core import OwnerCore
# from core.server_core import ServerCore


my_p2p_server_outer = None
# my_p2p_server_inner = None

def signal_handler(signal, frame):
	shutdown_server()

def shutdown_server():
	global my_p2p_server_outer
	my_p2p_server_outer.shutdown()
	# global my_p2p_server_inner
	# my_p2p_server_inner.shutdown()

def main():
	signal.signal(signal.SIGINT, signal_handler)
	global my_p2p_server_outer
	# my_p2p_server_outer = OwnerCore(50085, '10.84.247.68',50080) # Dtop
	# my_p2p_server_outer = OwnerCore(50070, '10.84.247.69',50080) # note
	my_p2p_server_outer = OwnerCore(50070, '192.168.0.142',50080) # note
	my_p2p_server_outer.start()
	my_p2p_server_outer.join_DMnetwork()
	#sleep(60)
	#print("sleep(60)")
	sleep(30)
	#print("sleep(120)")
	# my_p2p_server_outer.start_cross_reference()
	"""
	global my_p2p_server_inner
	my_p2p_server_inner = ServerCore(50087) # note
	my_p2p_server_inner.start()
	my_p2p_server_inner.join_network() 
	"""

if __name__ == '__main__':
	main()
