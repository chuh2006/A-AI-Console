import json
import os
import socket
import webbrowser

from ui.browser_ui_controller import BrowserUIController


def load_config(project_root: str) -> dict:
    config_path = os.path.join(project_root, "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"未找到配置文件: {config_path}。请先按现有终端模式准备好 config.json。"
        )

    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def pick_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"从端口 {preferred_port} 开始，连续 20 个端口都不可用。")

def get_local_ip() -> str:
    choice = input("请选择要绑定的IP地址:\n1. localhost\n2. any\n3. 其他 (请输入IP地址)\n请输入选项> ").strip()
    if choice == "1":
        return "127.0.0.1"
    elif choice == "2":
        return "0.0.0.0"
    else:
        return input("请输入IP地址: ").strip()

def main() -> None:
    project_root = os.path.dirname(os.path.abspath(__file__))
    config = load_config(project_root)
    host = get_local_ip()
    print(f"正在绑定到 {host}...")
    if not host:
        host = "0.0.0.0"
    port = pick_available_port(host, 8765)
    controller = BrowserUIController(project_root=project_root, config=config)
    webbrowser.open(f"http://{host}:{port}")
    controller.serve(host=host, port=port)

def start_browser_ui():
    main()

if __name__ == "__main__":
    main()
