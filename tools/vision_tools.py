import json
import pytesseract
from PIL import Image
import os

with open("config.json", "r") as f:
    config = json.load(f)
pytesseract.pytesseract.tesseract_cmd = config["settings"]["tesseract_path"]

def perform_ocr(image_paths: list[str]) -> str:
    """被大模型调用的实际本地函数"""
    try:
        returns = []
        for image_path in image_paths:
            img = Image.open(image_path)
            # 默认识别中英文
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            text = text.strip()
            returns.append("图一OCR结果：\n" + text + "\n")
        if not returns:
            return "未检测到任何文本"
        return "\n".join(returns)
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
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "用户上传的本地图片文件的绝对或相对路径"
                    },
                    "description": "用户上传的本地图片文件的绝对或相对路径的列表"
                }
            },
            "required": ["image_path"]
        }
    }
}

def object_detection(image_paths: list[str]) -> dict:
    """被大模型调用的实际本地函数"""
    try:
        from ultralytics import YOLO
    except ImportError:
        return {"result": "error", "message": "未安装 ultralytics 库，请先安装它以使用对象检测功能。"}
    try:
        model_path = os.path.join(os.path.dirname(__file__), 'local_models', 'yolo26s.pt')
        model = YOLO(model_path)  # 加载预训练模型
        returns = []
        for idx, image_path in enumerate(image_paths):
            results = model(image_path)  # 进行对象检测
            result = results[0]
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            names = model.names
            objects = []
            objects.append({
                "name": f"图{idx + 1}原始尺寸",
                "w": round(float(result.orig_shape[1]), 1),
                "h": round(float(result.orig_shape[0]), 1),
            })
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls_id = int(box.cls[0].item())
                obj_name = names.get(cls_id, str(cls_id))
                objects.append({
                    "name": obj_name,
                    "x": round(float((x1 + x2) / 2), 1),
                    "y": round(float((y1 + y2) / 2), 1),
                    "w": round(float(x2 - x1), 1),
                    "h": round(float(y2 - y1), 1),
                })
            returns.append(objects)
        return {"result": "success", "message": json.dumps(returns, ensure_ascii=False)}

    except Exception as e:
        return {"result": "error", "message": f"【对象检测失败】: {str(e)}"}

object_detection_tool_schema = {
    "type": "function",
    "function": {
        "name": "object_detection",
        "description": "当用户提供了本地图片路径，且你需要了解图片上的对象时，调用此工具进行对象检测。工具会返回图片尺寸和检测到对象名及其中心坐标和宽高。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "用户上传的本地图片文件的绝对或相对路径"
                    },
                    "description": "用户上传的本地图片文件的绝对或相对路径的列表"
                }
            },
            "required": ["image_path"]
        }
    }
}