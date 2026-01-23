import math
import hashlib

class BloomFilter:
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        self.size = self._calculate_size(expected_elements, false_positive_rate)
        self.hash_count = self._calculate_hash_count(self.size, expected_elements)
        self.bit_array = 0

    # 计算最优的位数组长度: m = -(n * ln(p)) / (ln(2))²
    def _calculate_size(self, n: int, p: float) -> int:
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    # 计算最优的哈希函数数量: k = (m/n) * ln(2)
    def _calculate_hash_count(self, m: int, n: int) -> int:
        k = (m / n) * math.log(2)
        return int(math.ceil(k))

    def _hash_functions(self, item: str) -> list[int]:
        hashes = []
        for i in range(self.hash_count):
            hash_obj = hashlib.md5((str(item) + str(i)).encode('utf-8'))
            hash_val = int(hash_obj.hexdigest(), 16)
            index = hash_val % self.size
            hashes.append(index)
        return hashes

    def add(self, item: str) -> None:
        for index in self._hash_functions(item):
            # 将对应位设为1（按位或操作）
            self.bit_array |= (1 << index)

    def contains(self, item: str) -> bool:
        for index in self._hash_functions(item):
            # 检查对应位是否为1（按位与操作）
            if not (self.bit_array & (1 << index)):
                return False
        return True


if __name__ == "__main__":
    # 初始化布隆过滤器：预期存储100个元素，误判率1%
    bf = BloomFilter(expected_elements=100, false_positive_rate=0.01)
    
    # 添加元素
    bf.add("熵")
    bf.add("最小二乘")
    bf.add("神经网络")
    
    # 查询元素
    print("熵 exists:", bf.contains("熵"))    
    print("最小二乘 exists:", bf.contains("最小二乘")) 
    print("神经网络 exists:", bf.contains("神经网络"))
    print("极大似然估计 exists:", bf.contains("极大似然估计"))    
    
    # 测试误判
    test_items = [f"test_{i}" for i in range(400)]
    # 只添加前100个元素
    for item in test_items[:100]:
        bf.add(item)
    # 测试之后未添加的元素
    false_positives = 0
    test_count = len(test_items[100:])
    for item in test_items[100:]:
        if bf.contains(item):
            false_positives += 1
    print(f"测试数量: {test_count}, 误判数量: {false_positives}, 误判率: {false_positives/test_count:.2%}")