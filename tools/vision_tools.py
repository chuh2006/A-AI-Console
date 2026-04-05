import json
import pytesseract
from PIL import Image
import tools.prompts as prompts

with open("config.json", "r") as f:
    config = json.load(f)
pytesseract.pytesseract.tesseract_cmd = config["settings"]["tesseract_path"]

def perform_ocr(image_path: str) -> str:
    """被大模型调用的实际本地函数"""
    try:
        img = Image.open(image_path)
        # 默认识别中英文
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        text = text.strip()
        return text if text else "【OCR完成，但未检测到任何有效文字】"
    except Exception as e:
        return f"【OCR提取失败】: {str(e)}"

# 提供给 DeepSeek 的工具说明书 (JSON Schema)
ocr_tool_schema = {
    "type": "function",
    "function": {
        "name": "perform_ocr",
        "description": "当用户提供了本地图片路径，且你需要了解图片上的文字内容时，调用此工具提取图片内的文本。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "用户上传的本地图片文件的绝对或相对路径"
                }
            },
            "required": ["image_path"]
        }
    }
}