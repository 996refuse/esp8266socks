from esp8266wifi import esp8266wifi
from socks5server import socks5server
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',    action='store', help='host to serve on',         type=str)
    parser.add_argument('--port',    action='store', help='port to serve on',         type=int)
    parser.add_argument('--serial',  action='store', help='serial port esp8266 is on',type=str)
    parser.add_argument('--boot',    dest="boot", action='store_true', help='boot esp8266 on start')
    parser.add_argument('--ssid',    action='store', help='configure wifi ssid',      type=str)
    parser.add_argument('--password',action='store', help='configure wifi password',  type=str)
    args = parser.parse_args()

    e = esp8266wifi(args.serial)
    s = socks5server(args.host, args.port)

    @e.onclose
    def onclose(linkid):
        print("#CLOSE", linkid)
        if s.esp8266_linkid_socks_map[linkid]:
            s.clean_sock_pair(s.esp8266_linkid_socks_map[linkid], "server socket closed", True)
            return
        s.esp8266_close_sync[linkid].release()

    @e.onconnect
    def onconnect(linkid):
        print("#CONNECT", linkid)
        s.esp8266_connect_sync[linkid].release()

    if args.boot:
        e.esp8266_boot(ssid=args.ssid, password=args.password)
    
    e.esp8266_daemon()

    @s.esp8266send
    def esp8266send(linkid, buf):
        return e.send(linkid, buf)

    @s.esp8266recv
    def esp8266recv(linkid):
        return e.recv(linkid)

    @s.esp8266close
    def esp8266close(linkid):
        return e.close(linkid)

    @s.esp8266connect
    def esp8266connect(linkid, host, port):
        return e.connect(linkid, host, port)

    s.run()
