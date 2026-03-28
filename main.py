import os
import json
import re
from ui.ui_controller import UIController
from core.llm_factory import LLMFactory
from core.session import ChatSession
import tools.prompts as prompts
from tools.utils import read_local_file, spawnRandomContext, getRandomSpawnerDescriptionContext
from tools.title_generator import generate_auto_title
import tools.reader as reader
from tools import costum_expections

def load_config() -> dict:
    """读取 main.py 同级目录下的 config.json"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    
    if not os.path.exists(config_path):
        # 如果文件不存在，给个默认模板并提示
        default_config = {
            "api_keys": {"deepseek": "", "gemini": "", "qwen": "", "doubao": ""},
            "settings": {"default_temperature": 1.0, "enable_system_prompt": False}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        raise FileNotFoundError(f"未找到配置文件！已在 {config_path} 自动生成模板，请填入 API Key 后重试。")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ui = UIController()
    def clean_temp_directory():
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    ui.display_warning(f"清理文件失败 {file_path}: {e}")
    clean_temp_directory()
    try:
        config = load_config()
        keys = config.get("api_keys", {})
        temperature = config.get("settings", {}).get("default_temperature", 1.0)
        enable_system_prompt = config.get("settings", {}).get("enable_system_prompt", True)
    except Exception as e:
        ui.display_error(str(e))
        return
    
    # 0. 目录存在性检查
    required_dirs = ["chat_result", "temp"]
    for d in required_dirs:
        dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), d)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

    # 1. 初始配置阶段
    ui.display_system("系统初始化完成，已加载配置文件。")
    use_history = ui.get_boolean_input("是否基于历史记录进行对话？")
    isRollBack = False

    if use_history:
        file_name = ui.get_user_input("请输入要读取的历史记录文件名（在chat_result目录下）：")
        conversation_history, temperature, full_history = reader.read_from_history(file_name)
        
        # --- 自动提取并清理标题 ---
        base_name = file_name.replace(".md", "")
        # 正则匹配并替换结尾的 (数字) 为空字符串
        chat_title = re.sub(r'\(\d+\)$', '', base_name)
        ui.display_system(f"已恢复对话，当前标题：{chat_title}")
        epoch = len([msg for msg in conversation_history if msg["role"] == "user"])
        session = ChatSession(first_time=False, enable_system_prompt=False)
        session.history = conversation_history
        session.full_context = full_history
    else:
        system_prompt = prompts.Prompts.universe_task_prompt
        session = ChatSession(system_prompt=system_prompt, first_time=True, enable_system_prompt=enable_system_prompt)
        epoch = 0
        chat_title = ""

    # 2. 主事件循环
    while True:
        try:
            clean_temp_directory()
            epoch += 1 if not isRollBack else 0
            isRollBack = False
            ui.display_system(f"--- 第 {epoch} 轮对话 ---")
            
            # 2.1 获取用户输入
            user_text = ui.get_user_input("请输入文本：")
            if user_text.lower() in ["q", "quit", "exit"]:
                break
            elif user_text.lower() == "format":
                filepath = ui.get_user_input("请输入文件路径：")
                user_text = read_local_file(filepath)
            elif user_text.lower() == "autoask":
                try:
                    question = session.get_question(keys.get("deepseek", ""))
                    ui.display_system(f"自动提问生成成功: {question}")
                    use_question = ui.get_boolean_input("是否使用自动提问的结果作为输入？")
                    if use_question:
                        user_text = question
                    else:
                        user_text = ui.get_user_input("请重新输入文本：")
                except costum_expections.AutoAskerException as e:
                    ui.display_error(f"自动提问生成失败: {e}")
                    user_text = ui.get_user_input("请重新输入文本：")
            session.add_epoch_count(epoch)  # 记录轮次到 Session
            if epoch == 1 and not chat_title:
                ui.display_system("正在根据您的输入生成对话标题...")
                ds_key = keys.get("deepseek")
                generated_title = generate_auto_title(ds_key, user_text)
                if generated_title:
                    chat_title = generated_title
                    ui.display_system(f"本场对话已自动命名为: {chat_title}")
                else:
                    ui.display_warning("标题生成失败，将使用默认时间戳命名。")

            # 2.2 获取模型与图片
            model_name = ui.get_model_choice()
            image_paths = ui.get_image_input(model_name)
            text_file_text = ui.get_text_file_input() if ui.get_boolean_input("是否上传文件？") else None
            if text_file_text:
                user_text += "\n\n用户随附了文件：\n<file>" + text_file_text + "</file>"

            # 2.3 针对问题的随机化处理
            is_q_random = ui.get_boolean_input("问题是否加随机？")
            final_user_text = user_text
            if is_q_random:
                random_ctx = getRandomSpawnerDescriptionContext(isFullRandom=ui.get_boolean_input("问题是否完全随机？"))
                final_user_text = spawnRandomContext(user_text, random_ctx)
                
            # 2.4 更新会话上下文 (写入 Session)
            session.add_user_message(content=final_user_text, original_text=user_text, images=image_paths)

            # 2.5 核心通信与重试环 (安全区)
            while True:
                try:
                    extra_kwargs = {}
                    if "gemini" in model_name:
                        extra_kwargs["enable_search"] = ui.get_boolean_input("是否启用联网搜索？")
                        extra_kwargs["think_level"] = ui.get_num_choice_input("请选择思考层级(minimal不代表一定不思考；high不代表一定思考)：", {"0": "minimal", "1": "low", "2": "medium", "3": "high"}) 
                    elif "qwen" in model_name:
                        extra_kwargs["enable_search"] = ui.get_boolean_input("是否启用联网搜索？")
                        if extra_kwargs["enable_search"]:
                            extra_kwargs["search_strategy"] = ui.get_num_choice_input("请设置设置搜索量级策略", {"1": "turbo", "2": "max", "3": "agent", "4": "agent_max"})
                        extra_kwargs["isQwenThinking"] = ui.get_en_or_disable_or_auto_input("是否启用Qwen思考功能？(启用后会整体提高回答质量，但是对用户强制纠正或者未知答案的问题容易陷入死循环，不建议开启。或者说千问这个模型本身就不建议使用。)\n请输入文本")
                    elif "doubao" in model_name:
                        extra_kwargs["enable_search"] = ui.get_boolean_input("是否启用联网搜索？")
                        extra_kwargs["reasoningEffort"] = ui.get_num_choice_input("请选择思考深度(minimal为关闭思考)：", {"0": "minimal", "1": "low", "2": "medium", "3": "high"})
                    elif "deepseek" in model_name:
                        if ui.get_boolean_input("是否启用DeepSeek思考", default=True):
                            model_name = "deepseek-reasoner"
                        else:
                            model_name = "deepseek-chat"

                    llm_client = LLMFactory.create_client(model_name, keys)
                    # 获取流生成器
                    stream = llm_client.chat_stream(
                        messages=session.get_history(),
                        temperature=temperature,
                        image_paths=image_paths, 
                        **extra_kwargs
                    )   
                    # 将流交给 UI 渲染
                    answer, thinking, meta = ui.render_stream(stream)   
                    # 走到这里说明网络请求完整无误地结束了
                    break

                except Exception as e:
                    ui.display_error(f"请求过程中发生错误: {e}")
                    if ui.get_boolean_input("是否重新发起本次请求？", default=True):
                        ui.display_system("正在重试...")
                        continue  # 留在当前内层循环，重新请求
                    else:
                        ui.display_warning("已取消重试。撤销刚才的问题。")
                        session.rollback_last_user_message() # 回滚状态
                        answer = None # 标记为失败
                        isRollBack = True
                        break
                except KeyboardInterrupt:
                    ui.display_warning("\n检测到强制中断 (Ctrl+C)。")
                    if ui.get_boolean_input("是否重新发起本次请求？", default=True):
                        ui.display_system("正在重试...")
                        continue  # 留在当前内层循环，重新请求
                    else:
                        ui.display_warning("已取消重试。撤销刚才的问题。")
                        session.rollback_last_user_message() # 回滚状态
                        answer = None # 标记为失败
                        isRollBack = True
                        break
            
            # 如果 answer 为 None，说明用户取消了重试，直接跳过后续处理，进入下一轮
            if not answer:
                continue

            # 2.6 针对回答的随机化处理
            is_a_random = ui.get_boolean_input("回答是否加随机？")
            final_answer = answer
            if is_a_random:
                random_ctx_ans = getRandomSpawnerDescriptionContext(isFullRandom=ui.get_boolean_input("回答是否完全随机？"))
                # 将随机字符添加到原答案中
                final_answer = spawnRandomContext(answer, random_ctx_ans)

            # 2.7 记录助手最终回答到 Session
            session.add_assistant_message(
                content=final_answer, 
                original_content=answer if is_a_random else None,
                thinking=thinking, 
                model_name=model_name,
                meta=meta
            )
            
            ui.display_system(f"当前 Token 估算：{session._calc_token_count()}")

            # 预留：每次循环结束前，可以询问图片是否继续保留
            if image_paths and not ui.get_boolean_input("是否继续使用上次的图片进行对话？"):
                image_paths = []

            # 清理 temp 目录下的文件
            clean_temp_directory()

        except KeyboardInterrupt:
            ui.display_warning("\n检测到强制中断 (Ctrl+C)。")
            break

    # 3. 程序退出清理
    ui.display_system("会话结束，正在保存记录...")
    filepath = session.save_to_disk(title=chat_title)
    ui.display_system(f"已保存至：{os.path.abspath(filepath)}")
    ui.stop_all_spinners()
    clean_temp_directory()
    
if __name__ == "__main__":
    main()