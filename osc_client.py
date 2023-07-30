from pythonosc.udp_client import SimpleUDPClient


class OSCclient():

    def __init__(self, ip: str, port: int):
        self.__ip = ip.replace(" ", "")
        self.__port = port

        self.__osc_client = SimpleUDPClient(self.ip, self.port)
        #self.__map = interp1d([20, 500], [0, 1])

    @property
    def ip(self):
        return self.__ip

    @ip.getter
    def ip(self) -> str:
        return self.__ip

    @ip.setter
    def ip(self, ip: str):
        self.__ip = ip
        self.__osc_client = SimpleUDPClient(self.ip, self.port)

    @property
    def port(self):
        return self.__port

    @port.getter
    def port(self) -> int:
        return self.__port

    @port.setter
    def port(self, port: int):
        self.__port = port
        self.__osc_client = SimpleUDPClient(self.ip, self.port)

    def send_osc(self, osc_address: str, value, map_to_resolume=False) -> None:
        if map_to_resolume:
            if value > 20 and value < 500:
                self.__osc_client.send_message(osc_address, float(value - 20) / float(480))
        else:
            self.__osc_client.send_message(osc_address, value)

    def __del__(self):
        del self.__osc_client
