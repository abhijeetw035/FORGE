def calculate_entropy(source_code: str):
    if not source_code:
        return 0
    
    from collections import Counter
    import math
    
    char_counts = Counter(source_code)
    total_chars = len(source_code)
    
    entropy = 0
    for count in char_counts.values():
        probability = count / total_chars
        entropy -= probability * math.log2(probability)
    
    return entropy
