import random

import ujson as json

from utils import (
    format_str,
    playsound,
    position_to_float,
    read_json,
    replace_wildcards,
    return_last_value,
    return_x64,
    sleep_for_cool,
)
from utils.environment import env
from utils.generator import Generator, inquire_anlas
from utils.image_tools import (
    change_the_mask_color,
    image_to_base64,
    is_fully_transparent,
    process_image_by_orientation,
    process_white_regions,
)
from utils.logger import logger
from utils.models import *  # noqa
from utils.variable import (
    return_quality_tags,
    return_skip_cfg_above_sigma,
    return_uc_preset_data,
    return_undesired_contentc_preset,
)

generator = Generator("https://image.novelai.net/ai/generate-image")


def main(
    model,
    positive_input,
    negative_input,
    furry_mode,
    add_quality_tags,
    undesired_contentc_preset,
    quantity,
    width,
    height,
    steps,
    prompt_guidance,
    prompt_guidance_rescale,
    variety,
    seed,
    sampler,
    noise_schedule,
    decrisp,
    sm,
    sm_dyn,
    legacy_uc,
    inpaint_input_image,
    strength,
    noise,
    naiv4vibebundle_file,
    normalize_reference_strength_multiple,
    character_reference_image,
    style_aware,
    fidelity,
    ai_choice,
    *args,
):
    with open("./outputs/temp_break.json", "w") as f:
        json.dump({"break": False}, f)

    if furry_mode == "🐾" and model not in ["nai-diffusion-3", "nai-diffusion-furry-3"]:
        positive_input = "fur dataset, " + positive_input

    director_reference_images = []
    director_reference_descriptions = []
    director_reference_information_extracted = []
    director_reference_strength_values = []
    director_reference_secondary_strength_values = []

    character_components = args[:30]
    character_components = [list(chunk) for chunk in zip(*[iter(character_components)] * 5)]
    v4_prompt_positive = []
    v4_prompt_negative = []
    characterPrompts = []
    for character_prompt in character_components:
        if character_prompt[-2]:
            x, y = position_to_float(character_prompt[2])
            center = {"x": x, "y": y}
            centers = [center]

            v4_prompt_positive.append({"char_caption": replace_wildcards(character_prompt[0]), "centers": centers})
            v4_prompt_negative.append({"char_caption": replace_wildcards(character_prompt[1]), "centers": centers})
            characterPrompts.append(
                {
                    "prompt": replace_wildcards(character_prompt[0]),
                    "uc": replace_wildcards(character_prompt[1]),
                    "center": center,
                    "enabled": True,
                }
            )

    vibe_components = args[30:]
    reference_image_multiple = []
    reference_information_extracted_multiple = []
    reference_strength_multiple = []
    if naiv4vibebundle_file or vibe_components[0]:
        model_function_map = {
            "nai-diffusion-4-5-full": nai45fvibe,  # noqa
            "nai-diffusion-4-5-curated": nai45cvibe,  # noqa
            "nai-diffusion-4-full": nai4fvibe,  # noqa
            "nai-diffusion-4-curated-preview": nai4cpvibe,  # noqa
            "nai-diffusion-3": nai3vibe,  # noqa
            "nai-diffusion-furry-3": nai3vibe,  # noqa
        }
        if model in ["nai-diffusion-3", "nai-diffusion-furry-3"]:
            vibe_images = [list(chunk) for chunk in zip(*[iter(vibe_components)] * 3)]
            for vibe_image in vibe_images:
                reference_image_multiple.append(image_to_base64(vibe_image[0]))
                reference_information_extracted_multiple.append(vibe_image[1])
                reference_strength_multiple.append(vibe_image[2])
        else:
            model_vibe_map = {
                "nai-diffusion-4-5-full": "v4-5full",
                "nai-diffusion-4-5-curated": "v4-5curated",
                "nai-diffusion-4-full": "v4full",
                "nai-diffusion-4-curated-preview": "v4curated",
            }
            vibe_data = read_json(naiv4vibebundle_file) or {}
            vibe_model_name = model_vibe_map.get(model)
            if not vibe_model_name:
                logger.warning(f"未找到 {model} 对应的 vibe 模型，跳过参考图。")
            else:
                vibe_images = vibe_data.get("vibes", [])
                if not vibe_images:
                    logger.warning("vibe bundle 中未包含 'vibes' 字段，参考图已忽略。")
                for vibe_image in vibe_images:
                    encodings = vibe_image.get("encodings", {})
                    model_encodings = encodings.get(vibe_model_name)
                    if not model_encodings:
                        logger.warning(
                            f"vibe 图像缺少 {vibe_model_name} 编码，文件: {naiv4vibebundle_file}，条目已跳过。"
                        )
                        continue
                    reference_image_multiple.append(return_last_value(model_encodings)["encoding"])
                    reference_strength_multiple.append(vibe_image.get("importInfo", {}).get("strength", 1))
    else:
        if character_reference_image and model in ["nai-diffusion-4-5-full", "nai-diffusion-4-5-curated"]:
            process_image_by_orientation(character_reference_image).save(
                image_path := "./outputs/temp_character_reference_image.png"
            )
            director_reference_images = [image_to_base64(image_path)]
            director_reference_descriptions = [
                {
                    "caption": {
                        "base_caption": "character&style" if style_aware else "character",
                        "char_captions": [],
                    },
                    "legacy_uc": False,
                }
            ]
            director_reference_information_extracted = [1]
            director_reference_strength_values = [1]
            director_reference_secondary_strength_values = [1 - fidelity]
            model_function_map = {
                "nai-diffusion-4-5-full": nai45fchar,  # noqa
                "nai-diffusion-4-5-curated": nai45cchar,  # noqa
            }
        else:
            model_function_map = {
                "nai-diffusion-4-5-full": nai45ft2i,  # noqa
                "nai-diffusion-4-5-curated": nai45ct2i,  # noqa
                "nai-diffusion-4-full": nai4ft2i,  # noqa
                "nai-diffusion-4-curated-preview": nai4cpt2i,  # noqa
                "nai-diffusion-3": nai3t2i,  # noqa
                "nai-diffusion-furry-3": naif3t2i,  # noqa
            }
    func = model_function_map.get(model)

    _type = "text2image"
    image_list = []

    for i in range(quantity):
        try:
            _break = read_json("./outputs/temp_break.json")
            if _break["break"]:
                logger.warning("已停止生成!")
                break

            if quantity != 1:
                logger.info(f"正在生成第 {i+1} 张图片...")
            else:
                logger.info("正在生成图片...")

            _positive_input = replace_wildcards(positive_input)
            _negative_input = replace_wildcards(negative_input)

            _seed = random.randint(1000000000, 9999999999) if seed == "-1" else int(seed)

            json_data = func(
                _input=format_str(
                    _positive_input + return_quality_tags(model) if add_quality_tags else _positive_input
                ),
                width=return_x64(width),
                height=return_x64(height),
                scale=prompt_guidance,
                sampler=sampler,
                steps=steps,
                ucPreset=return_uc_preset_data(model)[undesired_contentc_preset],
                qualityToggle=add_quality_tags,
                autoSmea=False,
                dynamic_thresholding=decrisp if model in ["nai-diffusion-3", "nai-diffusion-furry-3"] else False,
                legacy=False,
                add_original_image=True,
                cfg_rescale=prompt_guidance_rescale,
                noise_schedule=noise_schedule,
                legacy_v3_extend=False,
                skip_cfg_above_sigma=(return_skip_cfg_above_sigma(model) if variety else None),
                use_coords=not ai_choice,
                normalize_reference_strength_multiple=normalize_reference_strength_multiple,
                use_order=True,
                legacy_uc=legacy_uc if model in ["nai-diffusion-4-full", "nai-diffusion-4-curated-preview"] else False,
                seed=_seed,
                negative_prompt=format_str(
                    _negative_input + return_undesired_contentc_preset(model, undesired_contentc_preset)
                ),
                deliberate_euler_ancestral_bug=False,  # 仅在采样器为 k_euler_ancestral 时出现
                prefer_brownian=True,  # 仅在采样器为 k_euler_ancestral 时出现
                use_new_shared_trial=True,
                sm=sm,
                sm_dyn=sm_dyn,
                reference_image_multiple=reference_image_multiple,
                reference_information_extracted_multiple=reference_information_extracted_multiple,
                reference_strength_multiple=reference_strength_multiple,
                v4_prompt_positive=v4_prompt_positive,
                v4_prompt_negative=v4_prompt_negative,
                characterPrompts=characterPrompts,
                director_reference_images=director_reference_images,
                director_reference_descriptions=director_reference_descriptions,
                director_reference_information_extracted=director_reference_information_extracted,
                director_reference_strength_values=director_reference_strength_values,
                director_reference_secondary_strength_values=director_reference_secondary_strength_values,
            )

            if inpaint_input_image and inpaint_input_image.get("background"):
                (inpaint_input_image["background"]).save(image_path := "./outputs/temp_inpaint_image.png")
                layers = inpaint_input_image.get("layers") or []
                if not layers:
                    logger.warning("检测到基础图片但未提供图层，已跳过 Inpaint 处理。")
                    layers = [inpaint_input_image["background"]]
                layers[0].save(mask_path := "./outputs/temp_inpaint_mask.png")

                if is_fully_transparent(mask_path):
                    model_function_map = {
                        "nai-diffusion-4-5-full": nai45fi2i,  # noqa
                        "nai-diffusion-4-5-curated": nai45ci2i,  # noqa
                        "nai-diffusion-4-full": nai4fi2i,  # noqa
                        "nai-diffusion-4-curated-preview": nai4cpi2i,  # noqa
                        "nai-diffusion-3": nai3i2i,  # noqa
                        "nai-diffusion-furry-3": naif3i2i,  # noqa
                    }
                    _type = "image2image"
                else:
                    model_function_map = {
                        "nai-diffusion-4-5-full": nai45finfill,  # noqa
                        "nai-diffusion-4-5-curated": nai45cinfill,  # noqa
                        "nai-diffusion-4-full": nai4finfill,  # noqa
                        "nai-diffusion-4-curated-preview": nai4cpinfill,  # noqa
                        "nai-diffusion-3": nai3infill,  # noqa
                        "nai-diffusion-furry-3": naif3infill,  # noqa
                    }
                    _type = "inpaint"

                func = model_function_map.get(model)
                json_data = func(
                    json_data,
                    strength=strength,
                    noise=noise,
                    image=image_to_base64(image_path),
                    mask=image_to_base64(process_white_regions(change_the_mask_color(mask_path), mask_path)),
                    extra_noise_seed=_seed,
                    color_correct=False,
                )

            image_data = generator.generate(json_data)
            if image_data:
                parameters_data = json_data.get("parameters") or {}
                seed_value = parameters_data.get("seed", _seed)
                path = generator.save(image_data, _type, seed_value)
                image_list.append(path)
            if quantity != 1 and i != quantity - 1:
                sleep_for_cool(env.cool_time)
        except Exception as e:
            logger.error(f"出现错误: {e}")
            sleep_for_cool(5)

    playsound("./assets/finish.mp3")

    return image_list, f"处理完成! 剩余点数: {inquire_anlas()}"
