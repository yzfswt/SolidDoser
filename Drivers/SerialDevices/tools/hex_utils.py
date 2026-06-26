def dec_to_hex(dec_num):
    """
    十进制转十六进制字符串（大写，无0x前缀）
    :param dec_num: int
    :return: str
    """
    return format(dec_num, 'X')


def hex_to_dec(hex_str):
    """
    十六进制字符串转十进制（支持带或不带0x前缀）
    :param hex_str: str
    :return: int
    """
    return int(hex_str, 16)


def hex_to_bin(hex_str):
    """
    十六进制字符串转二进制字符串（无0b前缀）
    :param hex_str: str 十六进制字符串（支持带或不带0x前缀）
    :return: str 二进制字符串
    """
    # 如果有0x前缀，去掉它
    if hex_str.lower().startswith('0x'):
        hex_str = hex_str[2:]

    # 转换为十进制然后转换为二进制
    decimal_num = int(hex_str, 16)
    return format(decimal_num, 'b')


def hex_to_bin_padded(hex_str, bit_width=None):
    """
    十六进制字符串转二进制字符串（带填充，无0b前缀）
    :param hex_str: str 十六进制字符串（支持带或不带0x前缀）
    :param bit_width: int 指定二进制位宽，不足时前面补0。如果为None，则根据十六进制位数自动计算（每个十六进制位对应4个二进制位）
    :return: str 二进制字符串
    """
    # 如果有0x前缀，去掉它
    if hex_str.lower().startswith('0x'):
        hex_str = hex_str[2:]

    # 转换为十进制然后转换为二进制
    decimal_num = int(hex_str, 16)

    # 如果未指定位宽，根据十六进制位数计算（每个十六进制位对应4个二进制位）
    if bit_width is None:
        bit_width = len(hex_str) * 4

    return format(decimal_num, f'0{bit_width}b')


def append_crc16(hex_str):
    """
    对一串十六进制字符串追加CRC16校验（Modbus标准，低字节在前高字节在后）
    :param hex_str: str  # 例如 '010300000002'
    :return: str  # 追加CRC16后的十六进制字符串
    """
    data = bytes.fromhex(hex_str)
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    return hex_str + '{:02X}{:02X}'.format(crc_low, crc_high)
