import socket
import time
import threading
import select
import queue


chr_to_int = lambda x: x
encode_str = lambda x: x.encode()

VER = b'\x05'
METHOD = b'\x00'
SUCCESS = b'\x00'
SOCK_FAIL = b'\x01'
NETWORK_FAIL = b'\x02'
HOST_FAIL = b'\x04'
REFUSED = b'\x05'
TTL_EXPIRED = b'\x06'
UNSUPPORTED_CMD = b'\x07'
ADDR_TYPE_UNSUPPORT = b'\x08'
UNASSIGNED = b'\x09'

ADDR_TYPE_IPV4 = b'\x01'
ADDR_TYPE_DOMAIN = b'\x03'
ADDR_TYPE_IPV6 = b'\x04'

CMD_TYPE_CONNECT = b'\x01'
CMD_TYPE_TCP_BIND = b'\x02'
CMD_TYPE_UDP = b'\x03'

class socks5server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.esp8266_linkid_socks_map = {
            0: None,
            1: None,
            2: None,
            3: None,
            4: None,
        }
        self.esp8266_linkid_socks_map_q = queue.Queue(5)
        for i in range(5):
            self.esp8266_linkid_socks_map_q.put(i) 
        
    def buffer_receive(self, sock):
        buf = sock.recv(1024)
        # if len(buf) == 0:
        #     self.clean_sock_pair(sock, "client send empty string")
        #     return
        for linkid in self.esp8266_linkid_socks_map:
            if self.esp8266_linkid_socks_map[linkid] == sock:
                while buf:
                    send_buf = buf[:512]
                    buf = buf[512:]
                    self.esp8266_send(linkid, send_buf)
                    # time.sleep(0.2)
                return
        raise Exception("buffer_receive linkid socks map not found")
            
    def buffer_send(self, sock):
        for linkid in self.esp8266_linkid_socks_map:
            if self.esp8266_linkid_socks_map[linkid] == sock:
                buf = self.esp8266_recv(linkid)
                if buf:
                    sock.send(buf)
                return
        raise Exception("buffer_send linkid socks map not found")
        
    def clean_sock_pair(self, sock, error_msg):
        # print('clean_sock_pair due to error: %s' % error_msg)
        
        for linkid in self.esp8266_linkid_socks_map:
            if self.esp8266_linkid_socks_map[linkid] == sock:
                self.esp8266_linkid_socks_map[linkid] = None
                buf = self.esp8266_recv(linkid)
                if buf:
                    sock.send(buf)
                self.esp8266_close(linkid)
                sock.close()
                self.esp8266_linkid_socks_map_q.put(linkid)
                print('$$$$ SOCKS5 proxy from linkid %d destroyed' % linkid)
                break

    def establish_socks5(self, sock):
        """ Speak the SOCKS5 protocol to get and return dest_host, dest_port. """
        dest_host, dest_port = None, None
        try:
            ver, nmethods, methods = sock.recv(1), sock.recv(1), sock.recv(1)
            sock.sendall(VER + METHOD)
            ver, cmd, rsv, address_type = sock.recv(1), sock.recv(1), sock.recv(1), sock.recv(1)
            dst_addr = None
            dst_port = None
            if address_type == ADDR_TYPE_IPV4:
                dst_addr, dst_port = sock.recv(4), sock.recv(2)
                dst_addr = '.'.join([str(chr_to_int(i)) for i in dst_addr])
            elif address_type == ADDR_TYPE_DOMAIN:
                addr_len = ord(sock.recv(1))
                dst_addr, dst_port = sock.recv(addr_len), sock.recv(2)
                dst_addr = ''.join([chr(chr_to_int(i)) for i in dst_addr])
            elif address_type == ADDR_TYPE_IPV6:
                dst_addr, dst_port = sock.recv(16), sock.recv(2)
                tmp_addr = []
                for i in range(len(dst_addr) // 2):
                    tmp_addr.append(chr(dst_addr[2 * i] * 256 + dst_addr[2 * i + 1]))
                dst_addr = ':'.join(tmp_addr)
            dst_port = chr_to_int(dst_port[0]) * 256 + chr_to_int(dst_port[1])
            server_ip = ''.join([chr(int(i)) for i in socket.gethostbyname(self.host).split('.')])
            if cmd == CMD_TYPE_TCP_BIND:
                print('TCP Bind requested, but is not supported by socks5_server')
                sock.close()
            elif cmd == CMD_TYPE_UDP:
                print('UDP requested, but is not supported by socks5_server')
                sock.close()
            elif cmd == CMD_TYPE_CONNECT:
                sock.sendall(VER + SUCCESS + b'\x00' + b'\x01' + encode_str(server_ip +
                                        chr(self.port // 256) + chr(self.port % 256)))
                dest_host, dest_port = dst_addr, dst_port
            else:
                # Unsupport/unknown Command
                print('Unsupported/unknown SOCKS5 command requested')
                sock.sendall(VER + UNSUPPORTED_CMD + encode_str(server_ip + chr(self.port // 256) +
                                        chr(self.port % 256)))
                sock.close()
        except KeyboardInterrupt as e:
            print('Error in SOCKS5 establishment: %s' % e)

        return dest_host, dest_port

    def create_sock_pair(self, client_sock, addr):
        client_sock.settimeout(5)

        dest_host, dest_port = self.establish_socks5(client_sock)
        if None in (dest_host, dest_port):
            client_sock.close()
            return None
        
        linkid = self.esp8266_linkid_socks_map_q.get()
        if -1 == self.esp8266_connect(linkid, dest_host, dest_port):
            client_sock.close()
            self.esp8266_linkid_socks_map_q.put(linkid)
            return
        
        self.esp8266_linkid_socks_map[linkid] = client_sock

        client_sock.settimeout(1)
        client_sock.setblocking(0)

        print('$$$$ SOCKS5 proxy from %s:%d to %s:%d linkid %d established' %
                         (addr[0], addr[1], dest_host, dest_port, linkid))

    def accept_connection(self):
        (client, addr) = self.server_sock.accept()
        t = threading.Thread(target=self.create_sock_pair, args=(client, addr))
        # t.daemon = True
        t.start()

    def run(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen()
        print('Serving on %s:%d' % (self.host, self.port))

        while True:
            connected_sockets = list(filter(lambda x: x != None, self.esp8266_linkid_socks_map.values()))
            in_socks = [self.server_sock] + connected_sockets
            out_socks = connected_sockets
            in_ready, out_ready, err_ready = select.select(in_socks, out_socks, [], 0.1)

            for sock in in_ready:
                if sock == self.server_sock:
                    self.accept_connection()
                    continue
                try:
                    self.buffer_receive(sock)
                except Exception as e:
                    self.clean_sock_pair(sock, str(e))

            for sock in out_ready:
                try:
                    self.buffer_send(sock)
                except Exception as e:
                    self.clean_sock_pair(sock, str(e))

            for sock in err_ready:
                if sock == self.server_sock:
                    for linkid in self.esp8266_linkid_socks_map:
                        if self.esp8266_linkid_socks_map[linkid]:
                            self.clean_sock_pair(self.esp8266_linkid_socks_map[linkid], 'server socket closed')
                self.clean_sock_pair(sock, 'socket closed')
