import math
import os
from typing import Optional, Dict, Any, List

import numpy as np
import torch
import torchvision.transforms as T
from decord import VideoReader, cpu
from PIL import Image
from threading import Thread
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer, TextIteratorStreamer


class LocalInternVL:
    """
    将示例脚本包装为可复用的类，模型从本地 @models 目录加载。
    """

    IMAGENET_MEAN = (0.485, 0.456, 0.406)
    IMAGENET_STD = (0.229, 0.224, 0.225)

    def __init__(
        self,
        model_root: str = "./models",
        model_name: str = "InternVL3_5-8B-HF",
        dtype=torch.bfloat16,
        device: Optional[str] = None,
        device_map: Optional[str] = "auto",
        load_in_8bit: bool = False,
        use_flash_attn: bool = True,
        generation_config: Optional[Dict[str, Any]] = None,
    ):
        self.model_path = os.path.join(model_root, model_name)
        self.dtype = dtype
        self.model = AutoModel.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
            load_in_8bit=load_in_8bit,
            low_cpu_mem_usage=True,
            use_flash_attn=use_flash_attn,
            trust_remote_code=True,
            device_map=device_map,
        ).eval()
        if device_map is None and device is not None:
            self.model = self.model.to(device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=True, use_fast=False
        )
        self.generation_config = generation_config or dict(
            max_new_tokens=1024, do_sample=True
        )
        self.system_prompt = None

    @classmethod
    def build_transform(cls, input_size: int):
        mean, std = cls.IMAGENET_MEAN, cls.IMAGENET_STD
        return T.Compose(
            [
                T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
                T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
                T.ToTensor(),
                T.Normalize(mean=mean, std=std),
            ]
        )

    @staticmethod
    def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
        best_ratio_diff = float("inf")
        best_ratio = (1, 1)
        area = width * height
        for ratio in target_ratios:
            target_aspect_ratio = ratio[0] / ratio[1]
            ratio_diff = abs(aspect_ratio - target_aspect_ratio)
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_ratio = ratio
            elif ratio_diff == best_ratio_diff:
                if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                    best_ratio = ratio
        return best_ratio

    @classmethod
    def dynamic_preprocess(cls, image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height

        target_ratios = {
            (i, j)
            for n in range(min_num, max_num + 1)
            for i in range(1, n + 1)
            for j in range(1, n + 1)
            if i * j <= max_num and i * j >= min_num
        }
        target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

        target_aspect_ratio = cls.find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_width, orig_height, image_size
        )

        target_width = image_size * target_aspect_ratio[0]
        target_height = image_size * target_aspect_ratio[1]
        blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

        resized_img = image.resize((target_width, target_height))
        processed_images = []
        for i in range(blocks):
            box = (
                (i % (target_width // image_size)) * image_size,
                (i // (target_width // image_size)) * image_size,
                ((i % (target_width // image_size)) + 1) * image_size,
                ((i // (target_width // image_size)) + 1) * image_size,
            )
            split_img = resized_img.crop(box)
            processed_images.append(split_img)
        assert len(processed_images) == blocks
        if use_thumbnail and len(processed_images) != 1:
            thumbnail_img = image.resize((image_size, image_size))
            processed_images.append(thumbnail_img)
        return processed_images

    def load_image(self, image_file, input_size=448, max_num=12, device="cuda"):
        image = Image.open(image_file).convert("RGB")
        transform = self.build_transform(input_size=input_size)
        images = self.dynamic_preprocess(
            image, image_size=input_size, use_thumbnail=True, max_num=max_num
        )
        pixel_values = [transform(img) for img in images]
        pixel_values = torch.stack(pixel_values).to(self.dtype)
        if device is not None:
            pixel_values = pixel_values.to(device)
        return pixel_values

    def chat(
        self,
        question: str,
        pixel_values=None,
        generation_config: Optional[Dict[str, Any]] = None,
        num_patches_list=None,
        history=None,
        return_history: bool = True,
    ):
        cfg = generation_config or self.generation_config
        return self.model.chat(
            self.tokenizer,
            pixel_values,
            question,
            cfg,
            num_patches_list=num_patches_list,
            history=history,
            return_history=return_history,
        )

    def batch_chat(
        self,
        questions,
        pixel_values,
        num_patches_list,
        generation_config: Optional[Dict[str, Any]] = None,
    ):
        cfg = generation_config or self.generation_config
        return self.model.batch_chat(
            self.tokenizer,
            pixel_values,
            num_patches_list=num_patches_list,
            questions=questions,
            generation_config=cfg,
        )

    # 启用“thinking mode”，设置系统提示并建议调整采样参数
    def enable_thinking_mode(
        self,
        system_prompt: Optional[str] = None,
        do_sample: bool = True,
        temperature: float = 0.6,
    ):
        default_prompt = (
            'You are an AI assistant that rigorously follows this response protocol:\n\n'
            '1. First, conduct a detailed analysis of the question. Consider different angles, '
            'potential solutions, and reason through the problem step-by-step. Enclose this entire '
            'thinking process within <think> and </think> tags.\n\n'
            '2. After the thinking section, provide a clear, concise, and direct answer to the '
            "user's question. Separate the answer from the think section with a newline.\n\n"
            'Ensure that the thinking process is thorough but remains focused on the query. '
            'The final answer should be standalone and not reference the thinking section.'
        ).strip()
        self.system_prompt = system_prompt or default_prompt
        # 若模型支持 system_message，直接赋值；否则调用方可在 prompt 中手动拼接
        try:
            self.model.system_message = self.system_prompt
        except Exception:
            pass
        # 返回推荐的生成配置
        cfg = dict(self.generation_config)
        cfg["do_sample"] = do_sample
        cfg["temperature"] = temperature
        return cfg

    # 流式输出示例，返回生成文本与线程
    def stream_chat(
        self,
        question: str,
        pixel_values=None,
        generation_config: Optional[Dict[str, Any]] = None,
        num_patches_list=None,
    ):
        cfg = dict(generation_config or self.generation_config)
        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=10
        )
        cfg["streamer"] = streamer

        thread = Thread(
            target=self.model.chat,
            kwargs=dict(
                tokenizer=self.tokenizer,
                pixel_values=pixel_values,
                question=question,
                history=None,
                return_history=False,
                num_patches_list=num_patches_list,
                generation_config=cfg,
            ),
            daemon=True,
        )
        thread.start()

        generated_text = ""
        sep_token = getattr(getattr(self.model, "conv_template", None), "sep", None)
        for new_text in streamer:
            if sep_token is not None and new_text == sep_token:
                break
            generated_text += new_text
            print(new_text, end="", flush=True)
        return generated_text, thread

    @staticmethod
    def get_index(bound, fps, max_frame, first_idx=0, num_segments=32):
        if bound:
            start, end = bound[0], bound[1]
        else:
            start, end = -100000, 100000
        start_idx = max(first_idx, round(start * fps))
        end_idx = min(round(end * fps), max_frame)
        seg_size = float(end_idx - start_idx) / num_segments
        frame_indices = np.array(
            [
                int(start_idx + (seg_size / 2) + np.round(seg_size * idx))
                for idx in range(num_segments)
            ]
        )
        return frame_indices

    def load_video(self, video_path, bound=None, input_size=448, max_num=1, num_segments=32, device="cuda"):
        vr = VideoReader(video_path, ctx=cpu(0), num_threads=1)
        max_frame = len(vr) - 1
        fps = float(vr.get_avg_fps())

        pixel_values_list, num_patches_list = [], []
        transform = self.build_transform(input_size=input_size)
        frame_indices = self.get_index(bound, fps, max_frame, first_idx=0, num_segments=num_segments)
        for frame_index in frame_indices:
            img = Image.fromarray(vr[frame_index].asnumpy()).convert("RGB")
            tiles = self.dynamic_preprocess(
                img, image_size=input_size, use_thumbnail=True, max_num=max_num
            )
            pixel_values = [transform(tile) for tile in tiles]
            pixel_values = torch.stack(pixel_values).to(self.dtype)
            num_patches_list.append(pixel_values.shape[0])
            pixel_values_list.append(pixel_values)
        pixel_values = torch.cat(pixel_values_list)
        if device is not None:
            pixel_values = pixel_values.to(device)
        return pixel_values, num_patches_list

    # 示例方法：纯文本对话
    def demo_text_chat(self):
        question = "Hello, who are you?"
        response, history = self.chat(question)
        # 这里的 print 可根据需要开启
        # print(f"User: {question}\nAssistant: {response}")
        return response, history

    # 示例方法：单图单轮
    def demo_single_image(self, image_path="./examples/image1.jpg"):
        pixel_values = self.load_image(image_path, max_num=12)
        question = "<image>\nPlease briefly describe this picture with sad-sounding words and make your description around 20 words."
        response = self.chat(question, pixel_values=pixel_values, return_history=False)
        return response

    # 示例方法：视频多轮
    def demo_video_chat(self, video_path="./contentment.mp4"):
        pixel_values, num_patches_list = self.load_video(video_path, num_segments=10, max_num=1)
        pixel_values = pixel_values
        video_prefix = "".join([f"Frame{i+1}: <image>\n" for i in range(len(num_patches_list))])
        question = video_prefix + "Please briefly describe this video with contentment-sounding words and make your description vivid, emotional, and strictly under 60 words."
        response, history = self.chat(
            question, pixel_values=pixel_values, num_patches_list=num_patches_list, history=None
        )
        # 后续轮次示例：根据需要可继续使用 history
        return response, history


# 示例：如需直接运行，请取消注释
#if __name__ == "__main__":
#   internvl = LocalInternVL()
#   resp, hist = internvl.demo_text_chat()
#   print(resp)
#   resp_img = internvl.demo_single_image("/data/emo/ycy/Emoset/image/sadness/sadness_00001.jpg")
#   print(resp_img)
#   resp_video, hist_video = internvl.demo_video_chat("./contentment.mp4")
#   print(resp_video)
