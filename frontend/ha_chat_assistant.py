"""Home Assistant 智能家居助手 - Gradio Web界面

提供基于 Gradio 的 Web 界面，支持：
- 智能对话控制
- 设备控制
- 传感器数据查看
"""

from pathlib import Path

import dotenv
import gradio as gr

# 导入UI服务
from backend.source.ui_service.entity_service import entity_service
from backend.source.ui_service.chat_service import chat_service

# 导入日志工具
from backend.source.infrastructure.utils import logger
from frontend.api_layer.qwen_speech_model import qwen_speech_manager

# Load environment variables BEFORE importing modules that depend on them
dotenv.load_dotenv(".env")


# ==================== 设备控制选项卡 ====================

def update_entity_groups(device_type: str) -> tuple[gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """更新设备分组下拉框"""
    groups = entity_service.get_device_groups(device_type)
    if not groups:
        return (
            gr.Dropdown(choices=[], value=""),
            gr.Dropdown(choices=[], value=""),
            gr.Textbox(value=""),
        )
    return (
        gr.Dropdown(choices=groups, value=groups[0]),
        gr.Dropdown(choices=[], value=""),
        gr.Textbox(value="请选择设备分组和设备"),
    )


def update_entity_list(device_type: str, group_name: str) -> tuple[gr.Dropdown, gr.Textbox]:
    """更新设备列表下拉框"""
    devices = entity_service.get_device_list(device_type, group_name)
    if not devices:
        return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")

    return (
        gr.Dropdown(choices=devices, value=devices[0]),
        gr.Textbox(value="请选择设备查看状态"),
    )


def update_entity_status(device_type: str, group_name: str, entity_name: str) -> gr.Textbox:
    """更新设备状态显示"""
    status = entity_service.get_device_status(device_type, group_name, entity_name)
    if not status:
        return gr.Textbox(value="")

    return gr.Textbox(
        value=f"实体ID: {status['entity_id']}\n状态: {status['state']}\n最后更新: {status['last_updated']}"
    )


def control_entity(
    device_type: str, group_name: str, entity_name: str
) -> tuple[gr.Textbox, gr.Textbox]:
    """控制设备状态"""
    result = entity_service.control_device(device_type, group_name, entity_name)
    status_text = ""

    if result["success"]:
        status_info = entity_service.get_device_status(device_type, group_name, entity_name)
        if status_info:
            status_text = f"实体ID: {status_info['entity_id']}\n状态: {status_info['state']}\n最后更新: {status_info['last_updated']}"

    return gr.Textbox(value=result["message"]), gr.Textbox(value=status_text)


def refresh_device_list() -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """刷新设备列表"""
    device_types = entity_service.refresh_devices()

    choices = device_types if device_types else ["无可用设备"]
    value = device_types[0] if device_types else ""

    return (
        gr.Dropdown(
            choices=choices, value=value, interactive=bool(device_types), allow_custom_value=True
        ),
        gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True),
        gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True),
        gr.Textbox(value="设备列表已刷新"),
    )


def create_device_control_tab():
    """创建设备控制选项卡"""
    device_types = entity_service.refresh_devices()

    device_type = gr.Dropdown(
        label="设备类型",
        choices=device_types if device_types else ["无可用设备"],
        value=device_types[0] if device_types else "",
        interactive=bool(device_types),
        allow_custom_value=True,
    )

    entity_groups = gr.Dropdown(
        label="设备分组", choices=[], value="", interactive=False, allow_custom_value=True
    )

    entity_list = gr.Dropdown(
        label="设备列表", choices=[], value="", interactive=False, allow_custom_value=True
    )

    entity_status = gr.Textbox(label="设备状态", interactive=False)
    control_btn = gr.Button("切换状态")
    control_result = gr.Textbox(label="控制结果", interactive=False)

    device_type.change(
        fn=update_entity_groups,
        inputs=[device_type],
        outputs=[entity_groups, entity_list, entity_status],
    )

    entity_groups.change(
        fn=update_entity_list,
        inputs=[device_type, entity_groups],
        outputs=[entity_list, entity_status],
    )

    entity_list.change(
        fn=update_entity_status,
        inputs=[device_type, entity_groups, entity_list],
        outputs=[entity_status],
    )

    control_btn.click(
        fn=control_entity,
        inputs=[device_type, entity_groups, entity_list],
        outputs=[control_result, entity_status],
    )

    refresh_btn = gr.Button("刷新设备列表")
    refresh_btn.click(
        fn=refresh_device_list, outputs=[device_type, entity_groups, entity_list, entity_status]
    )

    gr.Markdown("## 设备控制")
    gr.Row([device_type, entity_groups])
    gr.Row([entity_list, entity_status])
    gr.Row([control_btn, refresh_btn])


# ==================== 传感器数据选项卡 ====================

def update_sensor_groups(sensor_type: str) -> tuple[gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """更新传感器分组下拉框"""
    groups = entity_service.get_sensor_groups(sensor_type)
    if not groups:
        return (
            gr.Dropdown(choices=[], value=""),
            gr.Dropdown(choices=[], value=""),
            gr.Textbox(value=""),
        )
    return (
        gr.Dropdown(choices=groups, value=groups[0]),
        gr.Dropdown(choices=[], value=""),
        gr.Textbox(value="请选择传感器分组和传感器"),
    )


def update_sensor_list(sensor_type: str, group_name: str) -> tuple[gr.Dropdown, gr.Textbox]:
    """更新传感器列表下拉框"""
    sensors = entity_service.get_sensor_list(sensor_type, group_name)
    if not sensors:
        return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")

    return (
        gr.Dropdown(choices=sensors, value=sensors[0]),
        gr.Textbox(value="请选择传感器查看数据"),
    )


def update_sensor_info(sensor_type: str, group_name: str, sensor_name: str) -> gr.Textbox:
    """更新传感器信息显示"""
    info = entity_service.get_sensor_info(sensor_type, group_name, sensor_name)
    if not info:
        return gr.Textbox(value="")

    info_lines = [
        f"实体ID: {info['entity_id']}",
        f"友好名称: {info['friendly_name']}",
        f"状态值: {info['state']}",
        f"最后更新: {info['last_updated']}",
    ]

    if "external_attributes" in info:
        info_lines.append("\n额外属性:")
        for attr_name, attr_value in info["external_attributes"].items():
            info_lines.append(f"  - {attr_name}: {attr_value}")

    return gr.Textbox(value="\n".join(info_lines))


def analyze_all_entities() -> gr.Textbox:
    """分析所有实体"""
    result = entity_service.analyze_all_entities()
    return gr.Textbox(value=result["message"])


def refresh_sensor_list() -> tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """刷新传感器列表"""
    return (
        gr.Dropdown(
            choices=["numeric", "text"], value="numeric", interactive=True, allow_custom_value=True
        ),
        gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True),
        gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True),
        gr.Textbox(value="传感器列表已刷新"),
    )


def create_sensor_data_tab():
    """创建传感器数据选项卡"""
    sensor_type = gr.Dropdown(
        label="传感器类型",
        choices=["numeric", "text"],
        value="numeric",
        interactive=True,
        allow_custom_value=True,
    )

    sensor_groups = gr.Dropdown(
        label="传感器分组", choices=[], value="", interactive=False, allow_custom_value=True
    )

    sensor_list = gr.Dropdown(
        label="传感器列表", choices=[], value="", interactive=False, allow_custom_value=True
    )

    sensor_info = gr.Textbox(label="传感器信息", interactive=False)
    analyze_btn = gr.Button("分析所有实体")
    analyze_result = gr.Textbox(label="分析结果", interactive=False)

    sensor_type.change(
        fn=update_sensor_groups,
        inputs=[sensor_type],
        outputs=[sensor_groups, sensor_list, sensor_info],
    )

    sensor_groups.change(
        fn=update_sensor_list,
        inputs=[sensor_type, sensor_groups],
        outputs=[sensor_list, sensor_info],
    )

    sensor_list.change(
        fn=update_sensor_info,
        inputs=[sensor_type, sensor_groups, sensor_list],
        outputs=[sensor_info],
    )

    analyze_btn.click(fn=analyze_all_entities, outputs=[analyze_result])

    refresh_btn = gr.Button("刷新传感器列表")
    refresh_btn.click(
        fn=refresh_sensor_list, outputs=[sensor_type, sensor_groups, sensor_list, sensor_info]
    )

    gr.Markdown("## 传感器数据")
    gr.Row([sensor_type, sensor_groups])
    gr.Row([sensor_list, sensor_info])
    gr.Row([analyze_btn, refresh_btn])


# ==================== 智能对话选项卡 ====================

async def process_message_wrapper(message: str, history: list) -> list[dict]:
    """
    处理用户消息并生成响应，返回符合Gradio Chatbot格式的历史记录
    """
    updated_history, voice_success, voice_error = await chat_service.process_message(message, history)

    if voice_error:
        logger.error(f"语音合成错误: {voice_error}")

    return updated_history


async def recognize_and_auto_submit(audio, chat_history):
    """语音识别并自动提交"""
    if not audio:
        return "", "请先录制语音", chat_history

    status = "正在进行语音识别..."
    logger.info(f"开始识别语音文件: {audio}")

    try:
        audio_path = Path(audio)

        if not audio_path.exists():
            return "", "错误：录音文件不存在或已损坏", chat_history

        if audio_path.stat().st_size == 0:
            return "", "错误：录音文件内容为空", chat_history

        text = qwen_speech_manager.audio_to_text(audio)
        if text:
            status = f"语音识别成功: {text[:30]}...，正在自动提交..."

            updated_history = await process_message_wrapper(text, chat_history)

            status = f"语音识别成功: {text[:30]}...，已自动提交并生成回复"
            return text, status, updated_history
        else:
            return "", "语音识别失败：可能是API密钥配置问题或网络连接问题", chat_history
    except Exception as e:
        error_msg = f"语音识别出错: {e!s}"
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return "", error_msg, chat_history


def create_chat_tab():
    """创建聊天标签页"""
    chat_history = gr.Chatbot(label="智能家居助手")
    user_input = gr.Textbox(label="请输入您的问题或命令")
    submit_btn = gr.Button("发送")
    clear_btn = gr.Button("清除对话历史")

    audio_input = gr.Audio(sources=["microphone"], type="filepath", label="语音输入")
    recognition_status = gr.Textbox(label="语音识别状态", interactive=False, value="就绪")

    submit_btn.click(
        fn=process_message_wrapper, inputs=[user_input, chat_history], outputs=[chat_history]
    )

    user_input.submit(
        fn=process_message_wrapper, inputs=[user_input, chat_history], outputs=[chat_history]
    )

    clear_btn.click(
        fn=lambda: ([], "", "就绪"), outputs=[chat_history, user_input, recognition_status]
    )

    audio_input.stop_recording(
        fn=recognize_and_auto_submit,
        inputs=[audio_input, chat_history],
        outputs=[user_input, recognition_status, chat_history],
    )

    gr.Markdown("## 智能对话")
    gr.Row([chat_history])
    gr.Row([user_input, submit_btn])
    gr.Row([audio_input, recognition_status])
    gr.Row([clear_btn])


# ==================== 主界面 ====================

def create_gradio_interface():
    """创建Gradio界面"""
    logger.info("正在创建Gradio界面...")

    with gr.Blocks(title="智能家居助手") as interface:
        gr.Markdown("# 智能家居助手")
        gr.Markdown("## 基于Home Assistant和Qwen大模型的智能控制中心")

        with gr.Tabs():
            with gr.Tab("智能对话"):
                create_chat_tab()

            with gr.Tab("设备控制"):
                create_device_control_tab()

            with gr.Tab("传感器数据"):
                create_sensor_data_tab()

    return interface


def main(server_port: int = 8083):
    """
    主函数

    Args:
        server_port: Web服务端口，默认8083
    """
    try:
        interface = create_gradio_interface()
        logger.info("Gradio界面创建完成")
        interface.launch(
            server_name="localhost",
            server_port=server_port,
            share=True,
            debug=True
        )
    except Exception as e:
        logger.error(f"程序运行出错: {e!s}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
