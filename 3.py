import requests
import concurrent.futures
import time
import re

def test_stream_speed(url, timeout=5):
    """
    测试单个直播源的连接速度
    返回连接时间（秒），如果连接失败返回None
    """
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 只读取一小部分数据来测试连接速度
        response.iter_content(chunk_size=1024)
        response.close()
        
        connect_time = time.time() - start_time
        return connect_time
    
    except:
        return None

def parse_ptv_file(filename):
    """
    解析ptv_list.txt文件，按频道分组直播源
    """
    channels = {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        with open(filename, 'r', encoding='gbk') as f:
            lines = f.readlines()
    
    current_channel = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # 检测是否是频道名称行（通常包含频道标识）
        if any(keyword in line.lower() for keyword in ['cctv', '卫视', 'channel', 'ch:']):
            current_channel = line
            channels[current_channel] = []
        elif current_channel and line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
            channels[current_channel].append(line)
    
    return channels

def auto_detect_channels(lines):
    """
    自动检测频道分组
    """
    channels = {}
    current_channel = "未分类"
    channels[current_channel] = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # 如果是明显的频道名称行
        if not line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')) and len(line) < 100:
            current_channel = line
            if current_channel not in channels:
                channels[current_channel] = []
        elif line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
            channels[current_channel].append(line)
    
    return channels

def main():
    input_file = "ptv_list.txt"
    output_file = "1.txt"
    
    print("正在读取直播源文件...")
    
    # 读取文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        try:
            with open(input_file, 'r', encoding='gbk') as f:
                lines = f.readlines()
        except:
            print("无法读取文件，请检查文件路径和编码")
            return
    
    # 解析频道
    channels = parse_ptv_file(input_file)
    if len(channels) == 0 or (len(channels) == 1 and "未分类" in channels):
        print("检测到文件格式不标准，尝试自动识别频道...")
        channels = auto_detect_channels(lines)
    
    print(f"发现 {len(channels)} 个频道")
    
    # 测试每个频道的直播源速度
    speed_results = {}
    
    for channel_name, urls in channels.items():
        print(f"\n正在测试频道: {channel_name}")
        print(f"该频道有 {len(urls)} 个直播源")
        
        # 使用多线程测试速度
        speed_tests = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(test_stream_speed, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    speed = future.result()
                    if speed is not None:
                        speed_tests.append((url, speed))
                        print(f"  ✓ {url[:50]}... 速度: {speed:.2f}秒")
                    else:
                        print(f"  ✗ {url[:50]}... 连接失败")
                except Exception as e:
                    print(f"  ✗ {url[:50]}... 错误: {e}")
        
        # 按速度排序（从快到慢）
        speed_tests.sort(key=lambda x: x[1])
        speed_results[channel_name] = speed_tests
    
    # 生成输出文件
    print(f"\n正在生成结果文件: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 直播源速度测试结果 - 按频道和速度排序\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# 格式: 频道名称,播放地址,连接速度(秒)\n\n")
        
        for channel_name, speed_list in speed_results.items():
            f.write(f"# {channel_name} - 共{len(speed_list)}个有效源\n")
            
            for url, speed in speed_list:
                f.write(f"{channel_name},{url},{speed:.2f}\n")
            
            f.write("\n")
    
    # 打印统计信息
    print(f"\n=== 测试完成 ===")
    print(f"输出文件: {output_file}")
    
    total_sources = sum(len(urls) for urls in channels.values())
    valid_sources = sum(len(speed_list) for speed_list in speed_results.values())
    
    print(f"总频道数: {len(channels)}")
    print(f"总直播源数: {total_sources}")
    print(f"有效直播源数: {valid_sources}")
    print(f"成功率: {valid_sources/total_sources*100:.1f}%" if total_sources > 0 else "0%")

if __name__ == "__main__":
    main()
