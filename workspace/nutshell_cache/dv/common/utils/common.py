def replicate_bits(binary_num, replication, num_bits):
    result = 0
    for i in range(num_bits):
        bit = (binary_num >> i) & 1
        for j in range(replication):
            result |= bit << (i * replication + j)
    return result
