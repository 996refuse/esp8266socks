import serial
import time
import threading
import select

class esp8266wifi:
    def __init__(self, port):
        # init esp8266
        self.esp8266_serial = serial.Serial(port, 115200, timeout=2)
        self.esp8266_serial_fileno = self.esp8266_serial.fileno()
        self.esp8266_readbuf = b""
        self.esp8266_writebuf = None

        self.esp8266_at_lock = threading.Lock()
        self.esp8266_at_done = threading.Semaphore(0)
        self.esp8266_at_result = None

        self.on_close   = lambda x: x
        self.on_connect = lambda x: x
        
        self.identities_msg = {
            b'0,CONNECT\r\n' : (0, self.id_connect),
            b'1,CONNECT\r\n' : (1, self.id_connect),
            b'2,CONNECT\r\n' : (2, self.id_connect),
            b'3,CONNECT\r\n' : (3, self.id_connect),
            b'4,CONNECT\r\n' : (4, self.id_connect),
            b'0,CLOSED\r\n'  : (0, self.id_closed),
            b'1,CLOSED\r\n'  : (1, self.id_closed),
            b'2,CLOSED\r\n'  : (2, self.id_closed),
            b'3,CLOSED\r\n'  : (3, self.id_closed),
            b'4,CLOSED\r\n'  : (4, self.id_closed),
            b'\r\n+IPD,0,'   : (0, self.id_ipd),
            b'\r\n+IPD,1,'   : (1, self.id_ipd),
            b'\r\n+IPD,2,'   : (2, self.id_ipd),
            b'\r\n+IPD,3,'   : (3, self.id_ipd),
            b'\r\n+IPD,4,'   : (4, self.id_ipd),
        }
        self.identities_at = {
            b'OK\r\n'        : "OK" ,
            b'ERROR\r\n'     : "ERROR",
            b'SEND OK\r\n'   : "SEND OK",
            b'SEND FAIL\r\n' : "SEND FAIL",
            b'busy s...'     : "BUSY SENDING",
            b'busy p...'     : "BUSY PROCESSING",
        }
        self.identities = {**self.identities_msg, **self.identities_at}
        
        self.esp8266_links_lock = threading.Lock()
        self.esp8266_links = {
            0: b'',
            1: b'',
            2: b'',
            3: b'',
            4: b'',
        }
        
    def onclose(self, func):
        self.on_close = func
    
    def onconnect(self, func):
        self.on_connect = func

    def id_connect(self, linkid):
        # print("id_connect %d" % linkid)
        self.on_connect(linkid)

    def id_closed(self, linkid):
        # print("id_closed %d" % linkid)
        self.on_close(linkid)

    def id_ipd(self, linkid):
        # print("id_ipd %d" % linkid)
        while True:
            try:
                colon = self.esp8266_readbuf.index(b":")
                break
            except:
                self.esp8266_readbuf += self.esp8266_serial.read_all()
        data_len = int(self.esp8266_readbuf[:colon].decode())
        self.esp8266_readbuf = self.esp8266_readbuf[colon+1:]
        while len(self.esp8266_readbuf) < data_len:
            self.esp8266_readbuf += self.esp8266_serial.read_all()
        with self.esp8266_links_lock:
            self.esp8266_links[linkid] += self.esp8266_readbuf[:data_len]
        self.esp8266_readbuf = self.esp8266_readbuf[data_len:]
        
    def esp8266_boot(self, ssid, password):
        self.esp8266_serial.write(b'ATE0\r\n')
        time.sleep(1)
        self.esp8266_serial.write(b'AT+CWMODE_CUR=1\r\n') # station mode
        time.sleep(1)
        self.esp8266_serial.write(b'AT+CIPMUX=1\r\n')     # multiple connections
        time.sleep(1)
        self.esp8266_serial.write(b'AT+CWJAP_CUR="%s","%s"\r\n' % (ssid.encode(), password.encode())) # connect wifi
        time.sleep(8)
        # self.esp8266_serial.write(b'AT+CIPSTATUS="%s","%s"\r\n' % (ssid.encode(), password.encode())) # connect wifi
        # time.sleep(1)
        print(self.esp8266_serial.read_all())
        
    def esp8266_resolve(self):
        index, res, kk = len(self.esp8266_readbuf), None, ""
        for key in self.identities:
            if key in self.esp8266_readbuf:
                if self.esp8266_readbuf.index(key) < index:
                    index, res, kk = self.esp8266_readbuf.index(key), self.identities[key], key
        if kk in self.identities:
            print("%%%%%%", self.esp8266_readbuf[:index+len(kk)])
            self.esp8266_readbuf = self.esp8266_readbuf[index+len(kk):]

        if kk in self.identities_at:
            self.esp8266_at_result = res
            self.esp8266_at_done.release()
        if kk in self.identities_msg:
            p, f = res
            f(p)
        return res
        
    def esp8266_daemon(self):
        def daemon():
            try:
                while True:
                    iready, oready, eready = select.select([self.esp8266_serial_fileno], [self.esp8266_serial_fileno], [], 0.1)
                    if iready:
                        self.esp8266_readbuf += self.esp8266_serial.read_all()
                        rs = True
                        while rs is not None:
                            rs = self.esp8266_resolve()
                    if oready:
                        if self.esp8266_writebuf is not None:
                            at, self.esp8266_writebuf = self.esp8266_writebuf, None
                            self.esp8266_serial.write(at)
                    if eready:
                        raise Exception("esp8266_daemon error")
            except Exception as e:
                print(str(e))
                self.esp8266_readbuf += self.esp8266_serial.read_all()
                print("==== esp8266_readbuf ====", self.esp8266_readbuf)
        d = threading.Thread(target=daemon)
        d.start()
        
    def esp8266_at(self, at):
        with self.esp8266_at_lock:
            time.sleep(0.2)
            self.esp8266_writebuf = at
            self.esp8266_at_done.acquire()
            return self.esp8266_at_result
    
    def connect(self, linkid, host, port):
        if "OK" == self.esp8266_at(('AT+CIPSTART=%d,"TCP","%s",%d\r\n' % (linkid, host, port)).encode()):
            return linkid
        else:
            return -1
        
    def close(self, linkid):
        return self.esp8266_at(('AT+CIPCLOSE=%d\r\n' % linkid).encode())
        
    def send(self, linkid, buf):
        if "OK" == self.esp8266_at(('AT+CIPSEND=%d,%d\r\n' % (linkid, len(buf))).encode()):
            while True:
                if b"> " in self.esp8266_readbuf:
                    break
            if "SEND OK" == self.esp8266_at(buf):
                return len(buf)
        return -1
        
    def recv(self, linkid):
        with self.esp8266_links_lock:
            buf, self.esp8266_links[linkid] = self.esp8266_links[linkid], b''
            return buf
