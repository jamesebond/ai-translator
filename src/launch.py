import yaml
import os
import gradio as gr
from utils.path import get_models
from utils.cuda import get_gpu_info
import json
import time
import importlib.util
from modules.file import FileReaderFactory, ExcelFileWriter

# 获取当前脚本所在目录的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))

# 构建baseConfig.yml和modelExplains.yml的绝对路径
file_path = os.path.join(script_dir, 'configs', 'baseConfig.yml')

with open(file_path, 'r') as file:
    yaml_data = yaml.load(file, Loader=yaml.FullLoader)

def webui():
    available_gpus = get_gpu_info()
    api_models = get_models(os.path.join(script_dir, 'models/API'))
    local_models = get_models(os.path.join(script_dir, 'models/local'))
    available_models = {**api_models, **local_models}
    available_languages = []
    
    def update_choices(selected_model):
        model_path = available_models[selected_model]
        support_language_path = os.path.join(model_path, 'support_language.json')
        readme_path = os.path.join(model_path, 'README.md')
        model_explanation = "This model doesn't have an explanation."
        if os.path.isfile(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as file:
                model_explanation = file.read()
        try:
            with open(support_language_path, 'r') as file:
                support_languages = json.load(file)
                original_language_choices = support_languages["original_language"]
                target_language_choices = support_languages["target_language"]
        except Exception as e:
            print(f"Error reading support_language.json: {e}")
            original_language_choices = []
            target_language_choices = []
        lora_list = [''] + [f for f in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, f)) and not f.startswith('.') and not f.startswith('_')]
        return gr.Dropdown(choices=original_language_choices), gr.Dropdown(choices=target_language_choices), gr.Dropdown(choices=lora_list), model_explanation
    
    def translate_excel(input_file, start_row, end_row, start_column, target_column, selected_model, selected_lora_model, selected_gpu, batch_size, original_language, target_languages):
        start_time = time.time()
        file_path = input_file.name
        reader = FileReaderFactory.create_reader(file_path)
        inputs = reader.extract_text(file_path, target_column, start_row, end_row)

        outputs = translate(inputs, selected_model, selected_lora_model, selected_gpu, batch_size, original_language, target_languages)

        excel_writer = ExcelFileWriter()
        print("Finally processed number: ", len(outputs))
        output_file = excel_writer.write_text(file_path, outputs, start_column, start_row, end_row)

        end_time = time.time()
        return f"Total process time: {int(end_time-start_time)}s", output_file
    
    def translate(inputs, selected_model, selected_lora_model, selected_gpu, batch_size, original_language, target_languages):
        if isinstance(inputs, str):
            inputs = [inputs]
        model_file_path = os.path.join(available_models[selected_model], 'model.py')
        # 检查文件是否存在
        if not os.path.exists(model_file_path):
            print(f"No model.py found in {available_models[selected_model]}")
            return
        spec = importlib.util.spec_from_file_location("model", model_file_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        outputs = {}
        if hasattr(model_module, 'Model'):
            model = model_module.Model(available_models[selected_model], selected_lora_model, selected_gpu)
            if hasattr(model, 'generate'):
                outputs = model.generate(inputs, original_language, target_languages, batch_size)
            else:
                print("Model class does not have a 'generate' method.")
        else:
            print("No Model class found in model.py.")
        return outputs

    with gr.Blocks(title="yonyou translator") as interface:
        with gr.Tabs():
            with gr.TabItem("Excel Translator"):
                with gr.Row():
                    with gr.Column():
                        input_file = gr.File()
                        with gr.Row():
                            start_row = gr.Number(value=yaml_data["excel_config"]["default_start_row"], label="起始行")
                            end_row = gr.Number(value=yaml_data["excel_config"]["default_end_row"], label="终止行")
                            target_column = gr.Textbox(value=yaml_data["excel_config"]["default_target_column"], label="目标列")
                            start_column = gr.Textbox(value=yaml_data["excel_config"]["default_start_column"], label="结果写入列")
                        with gr.Row():
                            selected_model = gr.Dropdown(choices=list(available_models.keys()), label="选择基模型")
                            selected_lora_model = gr.Dropdown(choices=[], label="选择Lora模型")
                            selected_gpu = gr.Dropdown(choices=available_gpus, label="选择GPU", value=available_gpus[0])
                            batch_size = gr.Number(value=10, label="批处理大小")
                        with gr.Row():
                            original_language = gr.Dropdown(choices=[], label="原始语言")
                            target_languages = gr.Dropdown(choices=[], label="目标语言", multiselect=True)
                        translate_button = gr.Button("Translate")
                    with gr.Column():
                        model_explanation_textbox = gr.Textbox(label="模型介绍", lines=5)
                        output_text = gr.Textbox(label="输出文本")
                        output_file = gr.File(label="翻译文件下载")
                selected_model.change(update_choices, inputs=[selected_model], outputs=[original_language, target_languages, selected_lora_model, model_explanation_textbox])
                translate_button.click(translate_excel, inputs=[input_file, start_row, end_row, start_column, target_column, selected_model, selected_lora_model, selected_gpu, batch_size, original_language, target_languages], outputs=[output_text, output_file])
            with gr.TabItem("Text Translator"):
                with gr.Row():
                    with gr.Column():
                        input_text = gr.Textbox(label="输入文本")
                        with gr.Row():
                            selected_model = gr.Dropdown(choices=available_models, label="选择基模型")
                            selected_lora_model = gr.Dropdown(choices=[], label="选择Lora模型")
                            selected_gpu = gr.Dropdown(choices=available_gpus, label="选择GPU", value=available_gpus[0])
                            batch_size = gr.Number(value=1, label="批处理大小", visible=False)
                        with gr.Row():
                            original_language = gr.Dropdown(choices=available_languages, label="原始语言")
                            target_languages = gr.Dropdown(choices=available_languages, label="目标语言", multiselect=True)
                        translate_button = gr.Button("Translate")
                    with gr.Column():
                        model_explanation_textbox = gr.Textbox(label="模型介绍", lines=5)
                        output_text = gr.Textbox(label="输出文本", lines=5)
                selected_model.change(update_choices, inputs=[selected_model], outputs=[original_language, target_languages, selected_lora_model, model_explanation_textbox])
                translate_button.click(translate, inputs=[input_text, selected_model, selected_lora_model, selected_gpu, batch_size, original_language, target_languages], outputs=output_text)
    interface.launch(share=True)
    # interface.launch(debug=True)

if __name__ == "__main__":
    webui()