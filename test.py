from perception_layer import parse_file_raw

# 替换为你的音频路径
audio_path = "/Users/tangyi/Desktop/cloud_computing/test_data/ml.mp3"
text = parse_file_raw(audio_path)
print("音频解析结果：")
print(text)