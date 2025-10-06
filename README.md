## 针对HomeAssistant的对外开放API对接UI Demo

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
