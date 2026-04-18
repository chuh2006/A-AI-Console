import os
import json
import re
from ui.ui_controller import UIController
print("\033[1;32m[S] 启动中")
print("\r[S] 导入核心库 [0/5]", end="")
from core.llm_factory import LLMFactory
from core.session import ChatSession
import tools.prompts as prompts
from tools.utils import spawnRandomContext, getRandomSpawnerDescriptionContext
from tools.title_generator import generate_auto_title
import tools.reader as reader
from tools import costum_expections
print("\033[0m", end="")

def load_config() -> dict:
    """读取 main.py 同级目录下的 config.json"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    
    if not os.path.exists(config_path):
        # 如果文件不存在，给个默认模板并提示
        default_config = {
            "api_keys": {
                "deepseek": "",
                "gemini": "",
                "qwen": "",
                "doubao": "",
                "tavily": "(如果deepseek需要启用搜索功能，此处必填)",
                "kimi": ""
                },
            "settings": {"default_temperature": 1.0, "enable_system_prompt": False}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        raise FileNotFoundError(f"未找到配置文件！已在 {config_path} 自动生成模板，请填入 API Key 后重试。")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(ui: UIController = None):
    force_quit = False
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
        default_model = config.get("settings", {}).get("default_model", "deepseek")
        if default_model and default_model in ["deepseek-reasoner", "deepseek-chat"]:
            default_model = "deepseek"
            ui.display_warning("不再使用reasoner和chat方式开关思考")
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

    
    current_model_name = default_model if default_model else ui.get_model_choice()
    current_model_name = ui.resolve_model_name(current_model_name)
    ui.display_system(f"当前模型已设置为: {current_model_name}")

    # 2. 主事件循环
    while True:
        try:
            save = True
            clean_temp_directory()
            epoch += 1 if not isRollBack else 0
            isRollBack = False
            ui.display_system(f"--- 第 {epoch} 轮对话 ---")

            # 2.1 获取用户输入
            chat_input = ui.get_chat_input("请输入文本", current_model=current_model_name)
            if chat_input["command"] == "quit":
                break
            if chat_input["command"] == "quit_without_saving":
                save = False
                break
            if chat_input["command"] == "system":
                new_system_prompt = chat_input["text"]
                session.edit_system_prompt(new_system_prompt)
                ui.display_system("系统提示已更新。")
                epoch -= 1  # 不增加轮次
                continue

            if chat_input["command"] == "model":
                new_model_name = ui.resolve_model_name(chat_input["argument"])
                if not new_model_name:
                    ui.display_warning("模型名不能为空。")
                    epoch -= 1  # 不增加轮次
                    continue
                if current_model_name != new_model_name:
                    session.switch_model(new_model_name, current_model_name)
                current_model_name = new_model_name
                ui.display_system(f"当前模型已切换为: {current_model_name}")
                epoch -= 1  # 不增加轮次
                continue

            if chat_input["command"] == "fork":
                fork_epoch = int(chat_input["argument"])
                if fork_epoch < 1 or fork_epoch >= epoch:
                    ui.display_warning(f"无效的轮次。请输入一个介于 1 和 {epoch} 之间的整数。")
                    epoch -= 1  # 不增加轮次
                    continue
                file_path = session.save_to_disk(title=chat_title)
                ui.display_system(f"已保存 fork 前的会话到 {file_path}")
                last_user = session.fork_to(fork_epoch)
                epoch = fork_epoch  # 将当前轮次设置为 fork 的轮次
                ui.display_system(f"已 fork 到第 {fork_epoch} 轮。当前轮次已更新为 {epoch}。上一条用户消息: {last_user}")
                continue

            user_text = chat_input["text"]
            if chat_input["command"] == "autoask":
                try:
                    question = session.get_question(keys.get("deepseek", ""))
                    ui.display_system(f"自动提问生成成功: {question}")
                    use_question = ui.get_boolean_input("是否使用自动提问的结果作为输入？")
                    if use_question:
                        user_text = question
                    else:
                        re_input = ui.get_chat_input("请重新输入文本")
                        if re_input["command"] == "quit":
                            break
                        user_text = re_input["text"]
                except costum_expections.AutoAskerException as e:
                    ui.display_error(f"自动提问生成失败: {e}")
                    re_input = ui.get_chat_input("请重新输入文本")
                    if re_input["command"] == "quit":
                        break
                    user_text = re_input["text"]
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
            model_name = current_model_name
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
                    new_model_name = model_name
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
                        if "deepseek-agent" in model_name:
                            new_model_name = "deepseek-reasoner"
                            extra_kwargs["enable_agent"] = True
                            if ui.get_boolean_input("是否启用交互式思考？", default=False):
                                extra_kwargs["enable_enhanced_thinking"] = True
                        elif model_name not in {"deepseek-chat", "deepseek-reasoner"}:
                            if ui.get_boolean_input("是否启用DeepSeek思考", default=True):
                                new_model_name = "deepseek-reasoner"
                                if ui.get_boolean_input("是否启用交互式思考", default=False):
                                    extra_kwargs["enable_enhanced_thinking"] = True
                            else:
                                new_model_name = "deepseek-chat"
                        if ui.get_boolean_input("是否启用联网搜索？", default=True if "agent" in model_name else False):
                            extra_kwargs["enable_search"] = True
                            extra_kwargs["searchEffort"] = ui.get_num_choice_input("请选择搜索量级", {"0": "time_only", "1": "minimal", "2": "low", "3": "medium", "4": "high", "5": "max", "6": "unlimited"}) if "reasoner" in new_model_name else "minimal"
                    elif "kimi" in model_name:
                        extra_kwargs["enable_thinking"] = ui.get_boolean_input("是否启用Kimi思考功能？", default=True)
                        extra_kwargs["enable_search"] = ui.get_boolean_input("是否启用Kimi联网搜索？")
                    elif "minimax" in model_name.lower():
                        extra_kwargs["enable_search"] = ui.get_boolean_input("是否启用联网搜索？")
                    elif "multi-assistant" in model_name:
                        ui.display_warning("multi-assistant 目前处于预览阶段，完全由AI生成代码，并且从未测试，可能存在不稳定和不可预知的表现，请谨慎选择。可直接 Ctrl+C 重新选择模型")

                    # 获取启用的工具列表
                    enabled_tools = []
                    if extra_kwargs.get("enable_search"):
                        enabled_tools.append("web_search")
                    session.add_enabled_tools(enabled_tools)  # 记录启用的工具到 Session
                    llm_client = LLMFactory.create_client(new_model_name, keys)
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
                    ui.display_warning("检测到强制中断 (Ctrl+C)。")
                    choice = ui.get_num_choice_input_num("是否要重试请求？", {"1": "保留消息并重试", "2": "重新输入消息并回滚", "3": "退出"})
                    if choice == "1":
                        ui.display_system("正在重试...")
                        continue  # 留在当前内层循环，重新请求
                    elif choice == "2":
                        ui.display_warning("已取消重试。撤销刚才的问题。")
                        session.rollback_last_user_message() # 回滚状态
                        answer = None # 标记为失败
                        isRollBack = True
                        break
                    else:
                        raise KeyboardInterrupt  # 退出整个程序
            
            # 如果 answer 为 None，说明用户取消了重试，直接跳过后续处理，进入下一轮
            if answer is None:
                continue

            # 2.6 针对回答的随机化处理
            is_a_random = False
            final_answer = answer if answer else "none"
            if answer:
                is_a_random = ui.get_boolean_input("回答是否加随机？")
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
            ui.display_warning("检测到强制中断 (Ctrl+C)。")
            save = ui.get_boolean_input("是否要保存当前对话？", default=True)
            force_quit = True
            break

    # 3. 程序退出清理
    ui.display_system("会话结束，正在保存记录...")
    if force_quit:
        ui.display_warning("最新一轮对话仅会保留用户输入")
    filepath = session.save_to_disk(title=chat_title) if save else None
    ui.display_system(f"已保存至：{os.path.abspath(filepath)}") if save else ui.display_system("未保存对话记录。")
    ui.stop_all_spinners()
    clean_temp_directory()
    
if __name__ == "__main__":
    ui = UIController()
    while True:
        ui.display_system("欢迎")
        try:
            main(ui)
        except KeyboardInterrupt:
            ui.display_warning("检测到强制中断 (Ctrl+C)。")
        except Exception as e:
            ui.display_error(f"程序发生未处理的错误: {e}")
        q = ui.get_boolean_input("是否重新开始一个新的对话？")
        if not q:
            ui.display_system("退出")
            break
