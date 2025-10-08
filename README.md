## 针对HomeAssistant的对外开放API对接UI Demo

### 项目架构图

```mermaid
graph TD
    subgraph 应用入口层
        A[ha_chat_assistant.py<br>主应用入口]
        C[analyze_entities.py<br>实体分析工具]
    end
  
    subgraph API对接接口层
        B1[home_assistant.py<br>Home Assistant API对接]
        B3[qwen_speech_model.py<br>语音API对接]
        B5[qwen_llm_model.py<br>大模型API对接]
        B2[home_assistant_llm_controller.py<br>API控制器]
    end
  
    subgraph 基础层
        B4[config.py<br>配置管理]
    end
  
    subgraph 外部服务
        D[Home Assistant API]
        E[Qwen LLM API]
        F[Qwen Speech API]
    end
    
    %% 调用关系
    A -->|调用| B1
    A -->|调用| B2
    A -->|调用| B3
    C -->|调用| B1
    C -->|调用| B2
    C -->|调用| B4
    B2 -->|调用| B1
    B2 -->|调用| B5
    B2 -->|调用| B4
    B1 -->|导入| B4
    B5 -->|导入| B4
    B3 -->|导入| B4
    B1 -->|HTTP请求| D
    B5 -->|HTTP请求| E
    B3 -->|HTTP请求| F
    
    %% 样式设置
    style A fill:#f9d5e5,stroke:#333,stroke-width:1px
    style C fill:#f9d5e5,stroke:#333,stroke-width:1px
    style B1 fill:#d0d0ff,stroke:#333,stroke-width:1px
    style B3 fill:#d0d0ff,stroke:#333,stroke-width:1px
    style B5 fill:#d0d0ff,stroke:#333,stroke-width:1px
    style B2 fill:#d0d0ff,stroke:#333,stroke-width:1px
    style B4 fill:#d5f9e3,stroke:#333,stroke-width:1px
    style D fill:#d5e5f9,stroke:#333,stroke-width:1px
    style E fill:#d5e5f9,stroke:#333,stroke-width:1px
    style F fill:#d5e5f9,stroke:#333,stroke-width:1px
```

### 主要模块说明

1. **应用入口层**

   - `ha_chat_assistant.py`: 主应用入口，提供Gradio UI界面，整合所有功能模块
   - `analyze_entities.py`: 实体分析工具，用于批量分析Home Assistant实体
2. **API对接接口层**

   - `home_assistant.py`: Home Assistant API对接接口，负责与Home Assistant系统交互
   - `qwen_speech_model.py`: 语音服务API对接接口，负责与语音识别和合成服务交互
   - `qwen_llm_model.py`: 大模型服务API对接接口，负责与Qwen大模型服务交互
   - `home_assistant_llm_controller.py`: 控制器，协调API接口间的调用
3. **基础层**

   - `config.py`: 配置文件，存储所有API密钥和配置参数
4. **外部服务**

   - Home Assistant API: 提供实体数据和控制功能
   - Qwen LLM API: 提供大模型能力
   - Qwen Speech API: 提供语音识别和合成能力

### 使用方法

文本依赖：requests，openpyxl，pandas，gradio

语音依赖：pyaudio

使用前需要在config中修改qwen和home assistant的key

```
cp source/config.py.sample source/config.py
```

然后就可以直接运行命令啦

```shell
python analyze_entities.py
python ha_chat_assistant.py
```

### 效果

#### 主界面展示
![主界面](images/hello.png)

#### 实体分析报告(LaTeX格式)
![分析报告](images/analysis_latex.png)

#### 实体数据导出(Excel格式)
![Excel数据](images/analysis_excel.png)

#### 灯光控制示例
![灯光控制](images/openlight.png)
