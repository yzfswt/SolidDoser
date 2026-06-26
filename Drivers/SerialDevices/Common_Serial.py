import queue
import serial
import threading
import time
from dataclasses import dataclass
from itertools import count


@dataclass
class _SerialRequest:
    priority: int
    sequence: int
    packet: bytes
    res_len: int
    response_queue: queue.Queue


class Common_Serial:
    def __init__(self, com_port):
        self.ser = serial.Serial(
            port=com_port,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
        )
        self.lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._is_closed = False
        self._req_counter = count()
        self._request_queue = queue.PriorityQueue()
        self._worker = threading.Thread(target=self._serial_worker, daemon=True)
        self._worker.start()
        print(f"Common_Serial initialized on port {com_port}")

    def crc16(self, data: bytes) -> bytes:
        crc = 0xFFFF
        for pos in data:
            crc ^= pos
            for _ in range(8):
                if (crc & 0x0001) != 0:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        crc_low = crc & 0xFF
        crc_high = (crc >> 8) & 0xFF
        return data + bytes([crc_low, crc_high])

    def _validate_response(self, recv: bytes, res_len: int, validator):
        if len(recv) == 0:
            return False, "timeout"
        if len(recv) != res_len:
            return False, f"length_mismatch(expected={res_len}, actual={len(recv)})"
        if validator is None:
            return True, "ok"
        try:
            validation_result = validator(recv)
            if isinstance(validation_result, tuple):
                return bool(validation_result[0]), str(validation_result[1])
            return bool(validation_result), "validator_failed"
        except Exception as exc:
            return False, f"validator_error({exc})"

    def _serial_worker(self):
        while True:
            _priority, _sequence, request = self._request_queue.get()
            if request is None:
                return

            try:
                with self.lock:
                    if self.ser is None or not self.ser.is_open:
                        request.response_queue.put((False, b"", "port_closed"))
                        continue
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                    print("发送数据:", request.packet.hex(" ").upper())
                    self.ser.write(request.packet)
                    recv = self.ser.read(request.res_len)
                    print("接收数据:", recv.hex(" ").upper())
                request.response_queue.put((True, recv, "ok"))
            except serial.SerialException as exc:
                request.response_queue.put((False, b"", f"serial_exception({exc})"))
            except Exception as exc:
                request.response_queue.put((False, b"", f"unexpected_exception({exc})"))

    def _send_transaction(
        self,
        packet: bytes,
        res_len: int,
        validator=None,
        retries: int = 0,
        retry_delay_s: float = 0.0,
        priority: int = 10,
    ):
        with self._state_lock:
            if self._is_closed:
                print("串口已关闭，无法发送")
                return b""

        max_attempts = max(1, retries + 1)
        last_error = "unknown"
        for attempt in range(1, max_attempts + 1):
            response_queue = queue.Queue(maxsize=1)
            request = _SerialRequest(
                priority=priority,
                sequence=next(self._req_counter),
                packet=packet,
                res_len=res_len,
                response_queue=response_queue,
            )
            self._request_queue.put((request.priority, request.sequence, request))

            wait_timeout = max(float(self.ser.timeout or 1) + 2.0, 3.0)
            try:
                success, recv, status = response_queue.get(timeout=wait_timeout)
            except queue.Empty:
                success, recv, status = False, b"", "worker_timeout"

            if not success:
                last_error = status
            else:
                is_valid, validation_status = self._validate_response(recv, res_len, validator)
                if is_valid:
                    return recv
                last_error = validation_status

            if attempt < max_attempts and retry_delay_s > 0:
                time.sleep(retry_delay_s)

        print(f"串口事务失败: {last_error}")
        return b""

    def sendcmd(
        self,
        cmd: bytes,
        res_len: int,
        validator=None,
        retries: int = 0,
        retry_delay_s: float = 0.0,
        priority: int = 10,
    ):
        packet = self.crc16(cmd)
        return self._send_transaction(
            packet,
            res_len,
            validator=validator,
            retries=retries,
            retry_delay_s=retry_delay_s,
            priority=priority,
        )

    def sendraw(
        self,
        data: bytes,
        res_len: int,
        validator=None,
        retries: int = 0,
        retry_delay_s: float = 0.0,
        priority: int = 10,
    ):
        return self._send_transaction(
            data,
            res_len,
            validator=validator,
            retries=retries,
            retry_delay_s=retry_delay_s,
            priority=priority,
        )

    def close(self):
        with self._state_lock:
            if self._is_closed:
                return
            self._is_closed = True

        self._request_queue.put((10**9, next(self._req_counter), None))
        if self._worker.is_alive():
            self._worker.join(timeout=2)

        with self.lock:
            if self.ser is not None and self.ser.is_open:
                self.ser.close()
                print("Serial port disconnected")

    def disconnect(self):
        self.close()


print("模块内容:", dir())