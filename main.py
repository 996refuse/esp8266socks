from esp8266wifi import esp8266wifi
from socks5server import socks5server
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',    action='store', help='host to serve on',         type=str)
    parser.add_argument('--port',    action='store', help='port to serve on',         type=int)
    parser.add_argument('--serial',  action='store', help='serial port esp8266 is on',type=str)
    parser.add_argument('--boot',    action='store', help='boot esp8266 on start',    type=bool)
    parser.add_argument('--ssid',    action='store', help='configure wifi ssid',      type=str)
    parser.add_argument('--password',action='store', help='configure wifi password',  type=str)
    args = parser.parse_args()

    e = esp8266wifi(args.serial)
    @e.onclose
    def onclose(linkid):
        print(linkid)
    @e.onconnect
    def onconnect(linkid):
        print(linkid)

    if args.boot:
        e.esp8266_boot(ssid=args.ssid, password=args.password)
    
    e.esp8266_daemon()

    s = socks5server(args.host, args.port)

