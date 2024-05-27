# esp8266socks
connect your PC to WIFI network by esp8266

![](https://github.com/996refuse/esp8266socks/demo.gif)

### hardware

pc -> USB Serial UART Converter -> esp01

notes:

1. chips on usb serial converter both pl2303, ch340 or ft232 are tested working fine. The converter's Gnd should wire to esp01's Gnd, otherwise the serial output is garbled.
2. 3.3v power supply to esp01 is important, esp01's unstable issue is mostly possibly caused by the power supply
3. require good heat dissipation on esp8266 chip, when the wifi is turning on, the power consumption is becoming high and temperature is becoming high, it's very possible lead to stuck.

### usage

```sh
# install dependancy package
pip install -r requirements.txt

python main.py --host <ip address> --port <port> --serial /dev/tty<serial port> --ssid <ssid> --password <password>
```

### software structure

```
     -------------                                                                            --------------
    |             | <- connect                                                    connect -> |              |   listen
    | esp8266wifi | <-   close    linkid <== esp8266_linkid_socks_map ==> sock    close   -> | socks5server | ========== socks5 proxy
    |             | <-    recv                                                    revc    -> |              |
    |             | <-    send                                                    send    -> |              |
     -------------                                                                            --------------
           ||
           ||
           || at command
           ||
           ||
       ----------
      | pyserial |
       ----------
```

### license

WTFPL http://www.wtfpl.net/

### donate

![image](https://raw.githubusercontent.com/996refuse/esp8266socks/master/donate.png)

### contact me

![image](https://raw.githubusercontent.com/996refuse/esp8266socks/master/wechat.png)
