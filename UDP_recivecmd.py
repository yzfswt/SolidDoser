import socket
import threading


class UDPSignalReceiver:
    """
    UDP信号接收器类
    启动后会在子线程中持续监听UDP信号，当接收到指定信号时执行事件委托
    """
    
    def __init__(self, host='127.0.0.1', port=8888):
        """
        初始化UDP信号接收器
        
        :param host: 监听的主机地址
        :param port: 监听的端口
        """
        self.host = host
        self.port = port
        self.udp_socket = None
        self.listen_thread = None
        self.is_running = False
        self.back_port = 8889
        # 事件委托，初始化为None
        self.on_receive_signal = None
        
    def start_listening(self):
        """
        启动UDP监听子线程
        """
        if not self.is_running:
            self.is_running = True
            # 创建UDP套接字
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 绑定本地地址和端口
            local_addr = (self.host, self.port)
            self.udp_socket.bind(local_addr)
            
            # 启动子线程进行监听
            self.listen_thread = threading.Thread(target=self._listen_loop)
            self.listen_thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
            self.listen_thread.start()
            print(f"UDP信号接收器已启动，监听 {self.host}:{self.port}")
    
    def _listen_loop(self):
        """
        UDP监听循环，在子线程中运行
        """
        try:
            while self.is_running:
                # 接收数据（缓冲区大小1024字节）
                data, sender_addr = self.udp_socket.recvfrom(1024)
                decoded_data = data.decode('utf-8')
                print(f"\n收到来自 {sender_addr} 的UDP消息：{decoded_data}")
                # 提取发送方端口并更新 self.back_port
                _, sender_port = sender_addr
                self.back_port = sender_port
                # 根据接收到的消息类型执行不同的事件委托调用方式
                if self.on_receive_signal is not None:
                    try:
                        if decoded_data == "OK":
                            # 如果收到的信息是"OK"，则直接执行事件委托（不带参数）
                            self.on_receive_signal()
                        else:
                            # 如果收到的信息不是"OK"，则将收到的信息作为事件委托的参数传入
                            self.on_receive_signal(decoded_data)
                    except Exception as e:
                        print(f"执行事件委托时发生错误：{e}")
        except Exception as e:
            if self.is_running:  # 如果不是因为停止而产生的错误，则打印
                print(f"UDP监听发生错误：{e}")
    
    def stop_listening(self):
        """
        停止UDP监听
        """
        if self.is_running:
            self.is_running = False
            # 关闭套接字
            if self.udp_socket:
                self.udp_socket.close()
            # 等待子线程结束
            if self.listen_thread and self.listen_thread.is_alive():
                self.listen_thread.join(timeout=1.0)
            print("UDP信号接收器已停止")
    
    def set_signal_handler(self, handler):
        """
        设置UDP信号处理的事件委托
        
        :param handler: 处理函数，可以是两种形式：
                       1. 不接收参数的函数（当接收到的消息是"OK"时调用）
                       2. 接收一个参数的函数（当接收到的消息不是"OK"时调用，参数为接收到的消息字符串）
        """
        self.on_receive_signal = handler


# 示例用法
if __name__ == "__main__":
    # 创建UDP信号接收器实例
    udp_receiver = UDPSignalReceiver()
    
    # 定义信号处理函数
    def handle_received_signal():
        print("处理接收到的OK信号")
        # 这里可以添加具体的信号处理逻辑
    
    # 设置信号处理函数
    udp_receiver.set_signal_handler(handle_received_signal)
    
    try:
        # 启动监听
        udp_receiver.start_listening()
        print("按Ctrl+C停止UDP接收器...")
        
        # 主线程保持运行
        while True:
            pass
    except KeyboardInterrupt:
        print("\n收到停止信号")
    finally:
        # 停止监听
        udp_receiver.stop_listening()