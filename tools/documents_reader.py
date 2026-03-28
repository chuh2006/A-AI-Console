import os
import fitz
import docx

class UnsupportedFileFormatError(Exception):
    pass

class DocumentParser:
    def __init__(self):
        # 常见的纯文本后缀
        self.text_extensions = {'.txt', '.md', '.py', '.js', '.c', '.json', '.html', '.csv'}

    def parse(self, file_path: str) -> str:
        """主入口：根据后缀分发解析任务"""
        if not os.path.exists(file_path):
            raise UnsupportedFileFormatError("[Error] 文件不存在")

        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                return self._parse_pdf(file_path)
            elif ext == '.docx':
                return self._parse_docx(file_path)
            elif ext in self.text_extensions:
                return self._parse_text(file_path)
            elif ext is None or ext == '':
                # 无后缀时尝试作为文本解析
                return self._parse_text(file_path)
            elif ext == '.doc':
                raise UnsupportedFileFormatError("不支持 .doc 格式，请转换为 .docx")
            else:
                raise UnsupportedFileFormatError(f"不支持的文件格式: {ext}")
        except Exception as e:
            raise UnsupportedFileFormatError(f"[解析失败] {str(e)}")

    def _parse_pdf(self, file_path: str) -> str:
        """解析 PDF 内容"""
        text_content = []
        # 使用 PyMuPDF 打开
        with fitz.open(file_path) as doc:
            for page in doc:
                # 提取每一页的文本
                text_content.append(page.get_text())
        return "\n".join(text_content)

    def _parse_docx(self, file_path: str) -> str:
        """解析 Word (.docx) 内容"""
        doc = docx.Document(file_path)
        # 提取所有段落的文本
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text)

    def _parse_text(self, file_path: str) -> str:
        """解析纯文本，自动尝试不同编码"""
        encodings = ['utf-8', 'gbk', 'utf-16', 'latin-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise UnsupportedFileFormatError("[Error] 无法识别文本编码格式")