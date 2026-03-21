import os
import time
import random
import string
import tools.kanalists as kanalists

HIRAGANA = kanalists.getHIRAGANA()
KATAKANA = kanalists.getKATAKANA()

def spawnRandomLetters(length: int = 1, isCapital: int = 0) -> str:
    letters = string.ascii_letters
    result = ''.join(random.choice(letters) for _ in range(length))
    if isCapital == 1:
        return result.upper()
    if isCapital == 2:
        return result.lower()
    return result

def spawnRandomKana(length: int = 1) -> str:
    kana = ''.join(HIRAGANA) + ''.join(KATAKANA)
    result = ''.join(random.choice(kana) for _ in range(length))
    return result

def spawnRandomDigits(length: int = 1) -> str:
    digits = string.digits
    result = ''.join(random.choice(digits) for _ in range(length))
    return result

def spawnRandom(length: int = 1, isCapital: int = 0) -> str:
    symbols = string.ascii_letters + string.digits + ''.join(HIRAGANA) + ''.join(KATAKANA) + string.ascii_letters + string.digits + string.punctuation
    result = ''.join(random.choice(symbols) for _ in range(length))
    if isCapital == 1:
        return result.upper()
    if isCapital == 2:
        return result.lower()
    return result

def spawnRandomNoKana(length: int = 1, isCapital: int = 0) -> str:
    symbols = string.ascii_letters + string.digits + string.punctuation
    result = ''.join(random.choice(symbols) for _ in range(length))
    if isCapital == 1:
        return result.upper()
    if isCapital == 2:
        return result.lower()
    return result

def getRandomString(context_input: dict | None = None) -> str:
    """
    Generates a random string based on the provided context.

    Parameters:
        context (dict | None): A dictionary specifying the type and properties of the string to generate.
            - type (str): The type of string to generate. Supported values are:
                - "letters": Random letters (optionally capitalized).
                - "digits": Random digits.
                - "kana": Random Japanese kana characters.
                - "all": Random combination of letters, digits, and kana.
                - "all_except_kana": Random combination of letters and digits (excluding kana).
            - length (int): The length of the string to generate. Must be a positive integer.
            - isCapital (int): If 1, generates capital letters (only applies to "letters" and "all" types).

    Returns:
        str: The generated random string.

    Raises:
        ValueError: If the length is not a positive integer or if an unsupported type is specified.
    """
    context = context_input.copy() if context_input is not None else None
    if context is None:
        context = {"type": "letters", "length": 1, "isCapital": 0}
    if isinstance(context.get("length"), list):
        context["length"] = random.randint(context["length"][0], context["length"][1])
    if int(context.get("length", 1)) <= 0 or (isinstance(context.get("length"), list) and (context.get("length")[0] <= 0 or context.get("length")[1] <= 0)):
        raise ValueError("Length must be a positive integer")
    if context.get("type") == "letters":
        return spawnRandomLetters(context.get("length", 1), context.get("isCapital", 0))
    if context.get("type") == "digits":
        return spawnRandomDigits(context.get("length", 1))
    if context.get("type") == "kana":
        return spawnRandomKana(context.get("length", 1))
    if context.get("type") == "all":
        return spawnRandom(context.get("length", 1), context.get("isCapital", 0))
    if context.get("type") == "all_except_kana":
        return spawnRandomNoKana(context.get("length", 1), context.get("isCapital", 0))
    raise ValueError("Unsupported type in context")
    
def getRandomSpawnerDescriptionContext(isFullRandom: bool = False) -> dict:
    """
    Generates a context dictionary for a random string spawner based on user input or random values.

    Args:
        isFullRandom (bool, optional): If True, all parameters are randomly generated. If False, parameters are obtained via user input. Defaults to False.

    Returns:
        dict: A dictionary containing the following keys:
            - "type" (str): The type of string to generate ("letters", "digits", "kana", "all", "all_except_kana").
            - "length" (int): The length of the string.
            - "isCapital" (int): Capitalization option (0: no distinction, 1: uppercase, 2: lowercase).
    """
    if isFullRandom:
        lengthRange = int(input("请输入随机字符串长度范围最大值[默认10]：") or 10)
        lengthDescription = ''
    else:
        lengthDescription = input("请输入随机字符串长度(num/num-num)：")
        lengthRange = 1
    isRandomLength = False
    if '-' in lengthDescription:
        isRandomLength = True
        lengthRangeList = lengthDescription.split('-')
    length = random.randint(1, lengthRange) if isFullRandom else (int(lengthDescription) if not isRandomLength else None)
    isCapital = random.randint(0, 2) if isFullRandom else int(input("请输入是否大写[0:不区分 / 1:大写 / 2:小写]：") or 0)
    types = {1: "letters", 2: "digits", 3: "kana", 4: "all", 5: "all_except_kana"}
    strType = types.get(random.randint(1, 5), "letters") if isFullRandom else types.get(
        int(input("请输入随机字符串类型[1:字母 / 2:数字 / 3:假名 / 4:全部类型 / 5:除假名]：")), "letters")
    return {
        "type": strType,
        "length": length,
        "isCapital": isCapital
    } if not isRandomLength else {
        "type": strType,
        "length": [int(lengthRangeList[0]), int(lengthRangeList[1])],
        "isCapital": isCapital
    }

def analysisStrRange(rangeStr: str, maxRange: int) -> list:
    ranges = []
    parts = rangeStr.split(' ')
    for part in parts:
        if '-' in part:
            start, end = part.split('-')
            if int(start) < 1 or int(end) > maxRange or int(start) > int(end):
                print(f"无效的范围：{part}，跳过")
                continue
            ranges.append((int(start), int(end)))
        else:
            try:
                index = int(part)
                if index < 1 or index > maxRange:
                    print(f"无效的索引：{part}，跳过")
                    continue
                ranges.append((index, index))
            except ValueError:
                print(f"无效的索引：{part}，跳过")
                continue
    return ranges

def spawnRandomContext(text: str, context: dict, strRange: str = "") -> str:
    """
    Generates a new string by appending a random string (from context) to each character in the input text.
    If a string range is provided, only characters within the specified ranges will have the random string appended.

    Args:
        text (str): The input text to process.
        context (dict): Context used by getRandomString to generate random strings.
        strRange (str, optional): A string representing character ranges (e.g., "1-3,5"). Defaults to "".

    Returns:
        str: The processed string with random strings appended as specified.
    """
    parts: list[str] = []
    if strRange == "":
        return ''.join(char + getRandomString(context) for char in text)
    maxRange = len(text)
    ranges = analysisStrRange(strRange, maxRange) if strRange and maxRange else []
    for index, char in enumerate(text, 1):
        in_range = any(start <= index <= end for start, end in ranges)
        if ranges and not in_range:
            parts.append(char)
        else:
            parts.append(char + getRandomString(context))
    return ''.join(parts)

def read_local_file(file_path: str) -> str:
    file_path = file_path.strip('"').strip("'")  # 去除可能的引号
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 时发生错误：{e}")
        return read_local_file(input("请输入正确的文件路径："))