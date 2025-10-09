import os
import sys
import gradio as gr
from typing import Dict, List, Any, Tuple, Optional

# 导入日志工具
from source.base_layer.utils import logger

# 导入模块化组件
from source.api_layer.home_assistant import hass_manager
from source.home_assistant_llm_controller_langgraph import hass_llm_controller_langgraph as hass_llm_controller
from source.api_layer.qwen_speech_model import qwen_speech_manager

import dotenv

dotenv.load_dotenv(".env")

# 设备控制选项卡相关函数
def update_entity_groups(device_type: str) -> Tuple[gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """
    更新设备分组下拉框
    """
    if not device_type or device_type not in hass_manager.entity_data.get("non_sensor_data", {}):
        return gr.Dropdown(choices=[], value=""), gr.Dropdown(choices=[], value=""), gr.Textbox(value="")
    
    entities = hass_manager.entity_data.get("non_sensor_data", {}).get(device_type, [])
    groups = list(hass_manager.group_entities_by_name(entities).keys())
    
    return gr.Dropdown(choices=groups, value=groups[0] if groups else ""), \
           gr.Dropdown(choices=[], value=""), \
           gr.Textbox(value="请选择设备分组和设备")

def update_entity_list(device_type: str, group_name: str) -> Tuple[gr.Dropdown, gr.Textbox]:
    """
    更新设备列表下拉框
    """
    if not device_type or not group_name or device_type not in hass_manager.entity_data.get("non_sensor_data", {}):
        return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")
    
    entities = hass_manager.entity_data.get("non_sensor_data", {}).get(device_type, [])
    grouped = hass_manager.group_entities_by_name(entities)
    
    if group_name in grouped:
        entity_choices = [e.get("friendly_name", e.get("entity_id", "未知")) for e in grouped[group_name]]
        return gr.Dropdown(choices=entity_choices, value=entity_choices[0] if entity_choices else ""), \
               gr.Textbox(value="请选择设备查看状态")
    
    return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")

def update_entity_status(device_type: str, group_name: str, entity_name: str) -> gr.Textbox:
    """
    更新设备状态显示
    """
    if not device_type or not group_name or not entity_name or device_type not in hass_manager.entity_data.get("non_sensor_data", {}):
        return gr.Textbox(value="")
    
    entities = hass_manager.entity_data.get("non_sensor_data", {}).get(device_type, [])
    grouped = hass_manager.group_entities_by_name(entities)
    
    if group_name in grouped:
        for entity in grouped[group_name]:
            if entity.get("friendly_name", entity.get("entity_id", "未知")) == entity_name:
                entity_id = entity.get("entity_id", "未知")
                state = entity.get("state", "未知")
                last_updated = entity.get("last_updated", "未知")
                return gr.Textbox(value=f"实体ID: {entity_id}\n状态: {state}\n最后更新: {last_updated}")
    
    return gr.Textbox(value="未找到设备信息")

def control_entity(device_type: str, group_name: str, entity_name: str) -> Tuple[gr.Textbox, gr.Textbox]:
    """
    控制设备状态
    """
    if not device_type or not group_name or not entity_name or device_type not in hass_manager.entity_data.get("non_sensor_data", {}):
        return gr.Textbox(value="控制失败：参数无效"), gr.Textbox(value="")
    
    entities = hass_manager.entity_data.get("non_sensor_data", {}).get(device_type, [])
    grouped = hass_manager.group_entities_by_name(entities)
    
    if group_name in grouped:
        for entity in grouped[group_name]:
            if entity.get("friendly_name", entity.get("entity_id", "未知")) == entity_name:
                entity_id = entity.get("entity_id", "未知")
                current_state = entity.get("state", "未知")
                new_state = "off" if current_state == "on" else "on"
                
                # 调用Home Assistant服务
                success_message = hass_manager.call_home_assistant_service(entity_id, f"turn_{new_state}")
                
                if "成功" in success_message:
                    # 更新实体数据
                    hass_manager.update_entity_data()
                    # 重新获取状态
                    status_text = update_entity_status(device_type, group_name, entity_name).value
                    return gr.Textbox(value=f"控制成功：已将 {entity_name} {new_state}"), gr.Textbox(value=status_text)
                else:
                    return gr.Textbox(value=f"控制失败：{success_message}"), gr.Textbox(value="")
    
    return gr.Textbox(value=f"控制失败：未找到设备 {entity_name}"), gr.Textbox(value="")

def refresh_device_list() -> Tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """
    刷新设备列表
    """
    hass_manager.update_entity_data()
    device_types = list(hass_manager.entity_data.get("non_sensor_data", {}).keys())
    
    # 确保即使没有设备类型，也不会有空值警告
    choices = device_types if device_types else ["无可用设备"]
    value = device_types[0] if device_types else ""
    
    return gr.Dropdown(choices=choices, value=value, interactive=bool(device_types), allow_custom_value=True), \
           gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True), \
           gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True), \
           gr.Textbox(value="设备列表已刷新")

# 创建设备控制选项卡
def create_device_control_tab():
    """
    创建设备控制选项卡
    """
    # 获取设备类型列表
    device_types = list(hass_manager.entity_data.get("non_sensor_data", {}).keys())
    
    # 设备类型选择，设置默认值为第一个设备类型（如果有）
    device_type = gr.Dropdown(
        label="设备类型", 
        choices=device_types if device_types else ["无可用设备"],
        value=device_types[0] if device_types else "",
        interactive=bool(device_types),
        allow_custom_value=True
    )
    
    # 设备分组
    entity_groups = gr.Dropdown(
        label="设备分组", 
        choices=[], 
        value="",
        interactive=False,
        allow_custom_value=True
    )
    
    # 设备列表
    entity_list = gr.Dropdown(
        label="设备列表", 
        choices=[], 
        value="",
        interactive=False,
        allow_custom_value=True
    )
    
    # 设备状态
    entity_status = gr.Textbox(label="设备状态", interactive=False)
    
    # 控制按钮
    control_btn = gr.Button("切换状态")
    
    # 控制结果
    control_result = gr.Textbox(label="控制结果", interactive=False)
    
    # 设置事件处理
    device_type.change(
        fn=update_entity_groups,
        inputs=[device_type],
        outputs=[entity_groups, entity_list, entity_status]
    )
    
    entity_groups.change(
        fn=update_entity_list,
        inputs=[device_type, entity_groups],
        outputs=[entity_list, entity_status]
    )
    
    entity_list.change(
        fn=update_entity_status,
        inputs=[device_type, entity_groups, entity_list],
        outputs=[entity_status]
    )
    
    control_btn.click(
        fn=control_entity,
        inputs=[device_type, entity_groups, entity_list],
        outputs=[control_result, entity_status]
    )
    
    # 刷新按钮
    refresh_btn = gr.Button("刷新设备列表")
    refresh_btn.click(
        fn=refresh_device_list,
        outputs=[device_type, entity_groups, entity_list, entity_status]
    )
    
    with gr.Column():
        gr.Markdown("## 设备控制")
        gr.Row([device_type, entity_groups])
        gr.Row([entity_list, entity_status])
        gr.Row([control_btn, refresh_btn])
        control_result
    return device_type, entity_groups, entity_list, entity_status, control_btn, refresh_btn, control_result

# 传感器数据选项卡相关函数
def update_sensor_groups(sensor_type: str) -> Tuple[gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """
    更新传感器分组下拉框
    """
    # 转换UI中的类型名称为后端使用的类型名称
    if sensor_type == "numeric":
        backend_sensor_type = "numeric_sensors"
    elif sensor_type == "text":
        backend_sensor_type = "text_sensors"
    else:
        return gr.Dropdown(choices=[], value=""), gr.Dropdown(choices=[], value=""), gr.Textbox(value="")
    
    sensor_key = f"{backend_sensor_type}_by_group"
    if sensor_key in hass_manager.entity_data.get("sensor_data", {}):
        groups = list(hass_manager.entity_data.get("sensor_data", {}).get(sensor_key, {}).keys())
        return gr.Dropdown(choices=groups, value=groups[0] if groups else ""), \
               gr.Dropdown(choices=[], value=""), \
               gr.Textbox(value="请选择传感器分组和传感器")
    
    return gr.Dropdown(choices=[], value=""), gr.Dropdown(choices=[], value=""), gr.Textbox(value="")

def update_sensor_list(sensor_type: str, group_name: str) -> Tuple[gr.Dropdown, gr.Textbox]:
    """
    更新传感器列表下拉框
    """
    # 转换UI中的类型名称为后端使用的类型名称
    if sensor_type == "numeric":
        backend_sensor_type = "numeric_sensors"
    elif sensor_type == "text":
        backend_sensor_type = "text_sensors"
    else:
        return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")
    
    if not group_name:
        return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")
    
    sensor_key = f"{backend_sensor_type}_by_group"
    if sensor_key in hass_manager.entity_data.get("sensor_data", {}) and group_name in hass_manager.entity_data.get("sensor_data", {}).get(sensor_key, {}):
        sensors = hass_manager.entity_data.get("sensor_data", {}).get(sensor_key, {}).get(group_name, [])
        sensor_choices = [s.get("friendly_name", s.get("entity_id", "未知")) for s in sensors]
        return gr.Dropdown(choices=sensor_choices, value=sensor_choices[0] if sensor_choices else ""), \
               gr.Textbox(value="请选择传感器查看数据")
    
    return gr.Dropdown(choices=[], value=""), gr.Textbox(value="")

def update_sensor_info(sensor_type: str, group_name: str, sensor_name: str) -> gr.Textbox:
    """
    更新传感器信息显示
    """
    # 转换UI中的类型名称为后端使用的类型名称
    if sensor_type == "numeric":
        backend_sensor_type = "numeric_sensors"
    elif sensor_type == "text":
        backend_sensor_type = "text_sensors"
    else:
        return gr.Textbox(value="")
    
    if not group_name or not sensor_name:
        return gr.Textbox(value="")
    
    sensor_key = f"{backend_sensor_type}_by_group"
    if sensor_key in hass_manager.entity_data.get("sensor_data", {}) and group_name in hass_manager.entity_data.get("sensor_data", {}).get(sensor_key, {}):
        for sensor in hass_manager.entity_data.get("sensor_data", {}).get(sensor_key, {}).get(group_name, []):
            if sensor.get("friendly_name", sensor.get("entity_id", "未知")) == sensor_name:
                entity_id = sensor.get("entity_id", "未知")
                state = sensor.get("state", "未知")
                unit = sensor.get("unit_of_measurement", sensor.get("unit", ""))
                last_updated = sensor.get("last_updated", "未知")
                
                # 创建包含更多详细信息的显示内容
                sensor_info_lines = [
                    f"实体ID: {entity_id}",
                    f"友好名称: {sensor.get('friendly_name', '未知')}",
                    f"状态值: {state}{unit}",
                    f"最后更新: {last_updated}"
                ]
                
                # 检查是否有更多属性可以显示
                if 'external_attributes' in sensor:
                    ext_attrs = sensor['external_attributes']
                    if ext_attrs:
                        sensor_info_lines.append("\n额外属性:")
                        for attr_name, attr_value in ext_attrs.items():
                            # 避免显示过长的属性值
                            if isinstance(attr_value, str) and len(attr_value) > 50:
                                attr_value = attr_value[:50] + "..."
                            sensor_info_lines.append(f"  - {attr_name}: {attr_value}")
                
                return gr.Textbox(value="\n".join(sensor_info_lines))
    
    return gr.Textbox(value="未找到传感器信息")

def analyze_all_entities() -> gr.Textbox:
    """
    分析所有实体
    """
    try:
        # 更新实体数据
        hass_manager.update_entity_data()
        
        # 分析实体（使用hass_llm_controller）
        summary, analysis = hass_llm_controller.analyze_entities(
            hass_manager.entity_data.get("sensor_data"),
            hass_manager.entity_data.get("non_sensor_data"),
        )
        
        # 保存结果（使用hass_llm_controller）
        summary_file, analysis_file = hass_llm_controller.save_analysis_results(summary, analysis)
        
        if summary_file and analysis_file:
            return gr.Textbox(value=f"分析完成！\n实体摘要已保存到: {summary_file}\n分析报告已保存到: {analysis_file}")
        else:
            return gr.Textbox(value="分析失败：无法保存结果")
    except Exception as e:
        return gr.Textbox(value=f"分析失败：{str(e)}")

def refresh_sensor_list() -> Tuple[gr.Dropdown, gr.Dropdown, gr.Dropdown, gr.Textbox]:
    """
    刷新传感器列表
    """
    hass_manager.update_entity_data()
    # UI中使用的传感器类型是'numeric'和'text'
    return gr.Dropdown(choices=["numeric", "text"], value="numeric", interactive=True, allow_custom_value=True), \
           gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True), \
           gr.Dropdown(choices=[], value="", interactive=False, allow_custom_value=True), \
           gr.Textbox(value="传感器列表已刷新")

# 创建传感器数据选项卡
def create_sensor_data_tab():
    """
    创建传感器数据选项卡
    """
    # 传感器类型选择，使用简化的类型名称
    sensor_type = gr.Dropdown(
        label="传感器类型", 
        choices=["numeric", "text"],
        value="numeric",
        interactive=True,
        allow_custom_value=True
    )
    
    # 传感器分组
    sensor_groups = gr.Dropdown(
        label="传感器分组", 
        choices=[], 
        value="",
        interactive=False,
        allow_custom_value=True
    )
    
    # 传感器列表
    sensor_list = gr.Dropdown(
        label="传感器列表", 
        choices=[], 
        value="",
        interactive=False,
        allow_custom_value=True
    )
    
    # 传感器信息
    sensor_info = gr.Textbox(label="传感器信息", interactive=False)
    
    # 分析按钮
    analyze_btn = gr.Button("分析所有实体")
    
    # 分析结果
    analyze_result = gr.Textbox(label="分析结果", interactive=False)
    
    # 设置事件处理
    sensor_type.change(
        fn=update_sensor_groups,
        inputs=[sensor_type],
        outputs=[sensor_groups, sensor_list, sensor_info]
    )
    
    sensor_groups.change(
        fn=update_sensor_list,
        inputs=[sensor_type, sensor_groups],
        outputs=[sensor_list, sensor_info]
    )
    
    sensor_list.change(
        fn=update_sensor_info,
        inputs=[sensor_type, sensor_groups, sensor_list],
        outputs=[sensor_info]
    )
    
    analyze_btn.click(
        fn=analyze_all_entities,
        outputs=[analyze_result]
    )
    
    # 刷新按钮
    refresh_btn = gr.Button("刷新传感器列表")
    refresh_btn.click(
        fn=refresh_sensor_list,
        outputs=[sensor_type, sensor_groups, sensor_list, sensor_info]
    )
    
    with gr.Column():
        gr.Markdown("## 传感器数据")
        gr.Row([sensor_type, sensor_groups])
        gr.Row([sensor_list, sensor_info])
        gr.Row([analyze_btn, refresh_btn])
        analyze_result
    return sensor_type, sensor_groups, sensor_list, sensor_info, analyze_btn, refresh_btn, analyze_result

def process_message_wrapper(message: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    处理用户消息并生成响应，返回符合Gradio Chatbot messages格式的历史记录
    """
    # 更新实体数据，确保设备列表是最新的
    hass_manager.update_entity_data()
    
    # 将新格式的历史记录转换为旧格式（元组列表）
    old_format_history = []
    i = 0
    while i < len(history):
        if i+1 < len(history) and history[i].get("role") == "user" and history[i+1].get("role") == "assistant":
            old_format_history.append((history[i]["content"], history[i+1]["content"]))
            i += 2
        else:
            i += 1

    # 调用process_message方法（使用hass_llm_controller）
    response = hass_llm_controller.process_home_assistant_message(message, old_format_history)
    
    # 添加新的用户消息和助手响应到历史记录
    updated_history = history.copy()
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "assistant", "content": response})
    
    # 自动生成并播放语音回复
    try:
        import os
        import tempfile
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, "auto_response_audio.wav")
        
        # 调用语音合成服务，使用默认语音类型
        success = qwen_speech_manager.text_to_audio(response, output_file, voice="female")
        if success:
            logger.info(f"自动生成语音回复成功")
        else:
            logger.error("语音合成失败")
    except Exception as e:
          logger.error(f"自动播放语音时出错: {str(e)}")
    
    return updated_history

# 创建对话选项卡
def create_chat_tab():
    """
    创建聊天标签页
    """
    # 创建聊天历史组件
    chat_history = gr.Chatbot(label="智能家居助手", type="messages")
    user_input = gr.Textbox(label="请输入您的问题或命令")
    submit_btn = gr.Button("发送")
    clear_btn = gr.Button("清除对话历史")
    
    # 语音功能组件
    # 注意：实际录音功能由Audio组件的麦克风图标处理
    audio_input = gr.Audio(sources=["microphone"], type="filepath", label="语音输入", visible=True)
    
    # 添加语音识别状态显示
    recognition_status = gr.Textbox(label="语音识别状态", interactive=False, value="就绪")
    
    # 新增自动提交功能的语音识别函数
    def recognize_and_auto_submit(audio, chat_history):
        if not audio:
            return "", "请先录制语音", chat_history
        
        # 更新状态
        status = "正在进行语音识别..."
        logger.info(f"开始识别语音文件: {audio}")
        
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(audio):
                return "", "错误：录音文件不存在或已损坏", chat_history
            
            # 获取文件大小，确保文件不为空
            if os.path.getsize(audio) == 0:
                return "", "错误：录音文件内容为空", chat_history
            
            # 调用语音识别服务
            text = qwen_speech_manager.audio_to_text(audio)
            if text:
                # 语音识别成功
                status = f"语音识别成功: {text[:30]}...，正在自动提交..."
                
                # 更新实体数据，确保设备列表是最新的
                hass_manager.update_entity_data()
                
                # 调用process_message_wrapper函数处理消息并生成回复，这样会包含TTS生成
                updated_history = process_message_wrapper(text, chat_history)
                
                status = f"语音识别成功: {text[:30]}...，已自动提交并生成回复"
                return text, status, updated_history
            else:
                # 语音识别失败
                return "", "语音识别失败：可能是API密钥配置问题或网络连接问题", chat_history
        except Exception as e:
            error_msg = f"语音识别出错: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return "", error_msg, chat_history
    
    # 设置事件处理
    submit_btn.click(
        fn=process_message_wrapper,
        inputs=[user_input, chat_history],
        outputs=[chat_history]
    )
    
    user_input.submit(
        fn=process_message_wrapper,
        inputs=[user_input, chat_history],
        outputs=[chat_history]
    )
    
    clear_btn.click(
        fn=lambda: ([], "", "就绪"),
        outputs=[chat_history, user_input, recognition_status]
    )
    
    # 语音识别事件处理 - 使用自动提交功能
    audio_input.stop_recording(
        fn=recognize_and_auto_submit,
        inputs=[audio_input, chat_history],
        outputs=[user_input, recognition_status, chat_history]
    )
    return chat_history, user_input, submit_btn, clear_btn


def create_gradio_interface():
    """
    创建Gradio界面
    """
    logger.info("正在创建Gradio界面...")
    
    # 创建标签页
    with gr.Blocks(title="智能家居助手") as interface:
        gr.Markdown("# 智能家居助手")
        gr.Markdown("## 基于Home Assistant和Qwen大模型的智能控制中心")
        
        with gr.Tabs():
            with gr.Tab("智能对话"):
                # 调用函数但不使用返回值，因为UI已在函数内部构建
                create_chat_tab()
            
            with gr.Tab("设备控制"):
                # 调用函数但不使用返回值，因为UI已在函数内部构建
                create_device_control_tab()
            
            with gr.Tab("传感器数据"):
                # 调用函数但不使用返回值，因为UI已在函数内部构建
                create_sensor_data_tab()
    
    return interface

# 主函数
def main(server_port):
    """
    主函数
    """
    try:
        # 创建并启动Gradio界面
        interface = create_gradio_interface()
        logger.info("Gradio界面创建完成")
        
        # 启动界面
        interface.launch(
            server_name="localhost",
            server_port=server_port,
            share=True,
            debug=True
        )
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()

# 执行主函数
if __name__ == "__main__":
    try:
        main(server_port=8080)
    except KeyboardInterrupt:
        logger.info("\n程序已停止")
    except Exception as e:
          logger.error(f"程序运行出错: {e}")