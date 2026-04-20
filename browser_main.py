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


def main() -> None:
    project_root = os.path.dirname(os.path.abspath(__file__))
    config = load_config(project_root)

    host = "127.0.0.1"
    port = pick_available_port(host, 8765)
    controller = BrowserUIController(project_root=project_root, config=config)
    webbrowser.open(f"http://{host}:{port}")
    controller.serve(host=host, port=port)

def start_browser_ui():
    main()

if __name__ == "__main__":
    main()
