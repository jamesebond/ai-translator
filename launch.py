from modules import initialize
import yaml
initialize.imports()

file_path = './configs/baseConfig.yml'

with open(file_path, 'r') as file:
    yaml_data = yaml.load(file, Loader=yaml.FullLoader)

# 打印读取的YAML数据
print(yaml_data['model_path']['mbart'])

def webui():
    import torch
    import gradio as gr
    from utils.path_utils import get_folders, path_foldername_mapping
    from modules.file import FileReaderFactory
    from modules.model import ModelFactory
    def get_gpu_info():
        print(torch.__version__)
        gpu_info = ["CPU"]
        try:
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_info.extend([torch.cuda.get_device_name(i) for i in range(gpu_count)])
        except Exception as e:
            pass
        return gpu_info
    available_gpus = get_gpu_info()
    model_list = []
    lora_model_list = []
    for key in yaml_data['model_path'].keys():
        if key == "lora":
            lora_model_list += get_folders(yaml_data['model_path'][key], key)
        else:
            model_list += get_folders(yaml_data['model_path'][key], key)
    model_dict = path_foldername_mapping(model_list)
    lora_model_dict = path_foldername_mapping(lora_model_list)
    available_models = list(model_dict.keys())
    available_lora_models = list(lora_model_dict.keys())
    available_languages = yaml_data["available_languages"]

    def upload_and_process_file(input_file, target_column, start_row, end_row, original_language, target_language, selected_gpu, selected_model):
        print("input_file", input_file)
        file_path = input_file.name
        reader = FileReaderFactory.create_reader(file_path)
        texts = reader.extract_text(file_path, target_column, start_row, end_row)
        print("model_dict", model_dict)
        print("selected_model", selected_model)
        selected = model_dict[selected_model]
        print("selected", selected)
        model_instance = ModelFactory.create_model(selected["model_type"], selected["path"], selected_gpu)
        outputs = []
        for input_text in texts:
            outputs.append(model_instance.generate(input_text, original_language, target_language))
        return outputs

    with gr.Blocks() as interface:
        with gr.Tabs():
            with gr.TabItem("Excel Translator"):
                with gr.Row():
                    with gr.Column():
                        input_file = gr.File()
                        with gr.Row():
                            target_column = gr.Textbox(value=yaml_data["excel_config"]["default_target_column"], label="目标列")
                            # start_index = gr.Number(value=1, label="起始编号")
                            start_row = gr.Number(value=yaml_data["excel_config"]["default_start_row"], label="起始行")
                            end_row = gr.Number(value=yaml_data["excel_config"]["default_end_row"], label="终止行")
                        with gr.Row():
                            original_language = gr.Dropdown(choices=available_languages, label="原始语言", value=yaml_data["default_original_language"])
                            target_language = gr.Dropdown(choices=available_languages, label="目标语言", value=yaml_data["default_target_language"])
                        with gr.Row():
                            selected_gpu = gr.Dropdown(choices=available_gpus, label="选择GPU", value=available_gpus[0])
                            selected_model = gr.Dropdown(choices=available_models, label="选择基模型", value=available_models[0] if len(available_models) else "")
                            # selected_model = gr.Dropdown(choices=available_models, label="选择基模型")
                            selected_model = gr.Dropdown(choices=available_lora_models, label="选择Lora模型", value=available_lora_models[0] if len(available_lora_models) else "")
                        translate_button = gr.Button("Translate")
                    with gr.Column():
                        output_frame = gr.DataFrame()
                        output_text = gr.Textbox(label="输出文本")
                # translate_button.click(upload_and_process_file, inputs=[input_file, target_column, start_index, start_row, end_row, original_language, target_language, selected_gpu, selected_model], outputs=output_text)
                translate_button.click(upload_and_process_file, inputs=[input_file, target_column, start_row, end_row, original_language, target_language, selected_gpu, selected_model], outputs=output_text)
            with gr.TabItem("Text Translator"):
                with gr.Row():
                    with gr.Column():
                        gr.Textbox(label="输入文本")
                        with gr.Row():
                            original_language = gr.Dropdown(choices=available_languages, label="原始语言", value=available_languages[0])
                            target_language = gr.Dropdown(choices=available_languages, label="目标语言", value=available_languages[1])
                        with gr.Row():
                            selected_gpu = gr.Dropdown(choices=available_gpus, label="选择GPU", value=available_gpus[0])
                            selected_model = gr.Dropdown(choices=available_models, label="选择基模型", value=available_models[0] if len(available_models) else "")
                            selected_model = gr.Dropdown(choices=available_lora_models, label="选择Lora模型", value=available_lora_models[0] if len(available_lora_models) else "")
                        translate_button = gr.Button("Translate")
                    with gr.Column():
                        output_text = gr.Textbox(label="输出文本")
    interface.launch()

if __name__ == "__main__":
    webui()