def extract_reactor_commands(file_path):
    """
    读取TXT文件，过滤注释行，提取S开头命令的名称和参数
    
    参数：
        file_path (str): TXT文件的路径
        
    返回：
        list: 存储有效命令的序列，每个元素为字典，包含"command_name"（命令名）和"parameters"（参数列表）
    """
    # 初始化存储有效命令的序列
    valid_commands = []
    
    # 打开文件并逐行处理（使用with语句自动关闭文件，避免资源泄漏）
    with open(file_path, 'r', encoding='utf-8') as file:
        # 逐行读取文件，记录行号（方便后续排查错误）
        for line_num, line in enumerate(file, start=1):
            # 去除行首尾的空白字符（空格、制表符、换行符等），避免因格式问题导致判断失误
            stripped_line = line.strip()
            
            # 1. 过滤注释行：以#开头的行，或去除空白后为空的行（空行可视为无效内容）
            if not stripped_line or stripped_line.startswith('#'):
                continue
            
            # 2. 处理S开头的有效命令行
            if stripped_line.startswith('S '):
                try:
                    # 步骤1：提取命令名称（S 后面到 ( 前面的部分）
                    # 示例：S REACTOR_SOLUTION_ADD(reactor_reactor1,solution.A,20); 
                    # 截取后得到 "REACTOR_SOLUTION_ADD"
                    command_start = len('S ')  # S后面有一个空格，从空格后开始截取
                    bracket_index = stripped_line.find('(')  # 找到第一个'('的位置
                    if bracket_index == -1:
                        raise ValueError("命令格式错误：缺少 '('")  # 无'('则视为格式错误
                    command_name = stripped_line[command_start:bracket_index].strip()
                    if not command_name:
                        raise ValueError("命令格式错误：缺少命令名称")  # 命令名为空视为错误
                    
                    # 步骤2：提取括号中的参数（从( 后面到 ) 前面的部分）
                    # 示例：截取后得到 "reactor_reactor1,solution.A,20"
                    param_part = stripped_line[bracket_index + 1:].split(')')[0].strip()
                    if not param_part:
                        # 无参数情况（如可能存在的S EMPTY_COMMAND();），参数列表设为空
                        parameters = []
                    else:
                        # 按逗号分割参数，去除每个参数首尾的空白（处理可能的格式空格，如"a, b, c"）
                        parameters = [param.strip() for param in param_part.split(',')]
                    
                    # 步骤3：将命令名和参数存入字典，再加入序列
                    valid_commands.append({
                        "command_name": command_name,
                        "parameters": parameters
                    })
                
                # 捕获命令格式错误，提示具体行号方便排查
                except ValueError as e:
                    print(f"警告：第{line_num}行命令格式错误，跳过该行。错误信息：{e}")
                    continue
                except IndexError:
                    print(f"警告：第{line_num}行命令缺少 ')'，跳过该行。")
                    continue
    
    return valid_commands


# ------------------- 示例：调用函数并打印结果 -------------------
if __name__ == "__main__":
    # 替换为你的TXT文件路径（如"示例命令2.txt"，若文件在其他目录需写完整路径，如"D:/data/示例命令2.txt"）
    txt_file_path = "E:\PJ_Project_Software\ActionSequence\orderlist1.txt"
    
    # 提取命令
    reactor_commands = extract_reactor_commands(txt_file_path)
    
    # 打印结果
    print("提取到的有效命令序列：")
    print("-" * 50)
    for idx, cmd in enumerate(reactor_commands, start=1):
        print(f"命令{idx}：")
        print(f"  命令名：{cmd['command_name']}")
        print(f"  参数列表：{cmd['parameters']}")
        print("-" * 50)