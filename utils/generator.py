import io
import os
import zipfile
from datetime import date
from pathlib import Path

import requests
import ujson as json

from utils import generate_random_str
from utils.environment import env
from utils.logger import logger
from utils.models.headers import headers

MAX_IMAGE_STORAGE_BYTES = 50 * 1024 * 1024
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _list_saved_images(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(path)
    files.sort(key=lambda f: f.stat().st_ctime)
    return files


def _enforce_storage_budget(root: Path):
    files = _list_saved_images(root)
    total = sum(path.stat().st_size for path in files)
    while total > MAX_IMAGE_STORAGE_BYTES and files:
        oldest = files.pop(0)
        try:
            size = oldest.stat().st_size
        except FileNotFoundError:
            continue
        try:
            oldest.unlink()
            total -= size
            logger.info(f"已删除旧图片以释放空间: {oldest}")
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning(f"无法删除 {oldest}: {exc}")
            break


def inquire_anlas():
    try:
        rep = requests.get(
            "https://api.novelai.net/user/subscription",
            headers=headers,
            proxies=(
                {
                    "http": env.proxy,
                    "https": env.proxy,
                }
                if env.proxy is not None
                else None
            ),
        )
        if rep.status_code == 200:
            return rep.json()["trainingStepsLeft"]["fixedTrainingStepsLeft"]
        return -1
    except Exception as e:
        return str(e)


class Generator:
    def __init__(self, url):
        self.url = url

    def generate(self, json_data: dict):
        with open("last.json", "w", encoding="utf-8") as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)
        try:
            rep = requests.post(
                url=self.url,
                json=json_data,
                headers=headers,
                proxies=(
                    {
                        "http": env.proxy,
                        "https": env.proxy,
                    }
                    if env.proxy is not None
                    else None
                ),
            )
            if (status_code := rep.status_code) != 200:
                logger.debug(f"本次请求状态码: {status_code}")
                logger.debug(rep.json()["message"])
            logger.success(f"请求成功! 剩余点数: {inquire_anlas()}")
            with zipfile.ZipFile(io.BytesIO(rep.content), mode="r") as zip:
                if json_data.get("req_type") == "bg-removal":
                    with (
                        zip.open("image_0.png") as masked,
                        zip.open("image_1.png") as generated,
                        zip.open("image_2.png") as blend,
                    ):
                        return masked.read(), generated.read(), blend.read()
                with zip.open("image_0.png") as image:
                    return image.read()
        except Exception as e:
            logger.error(f"出现错误: {e}")
            return None

    def save(self, image_data, type, seed):
        if image_data:
            base_path = (
                f"./outputs/{env.custom_path}".replace("<类型>", type)
                .replace("<日期>", str(date.today()))
                .replace("<种子>", str(seed))
                .replace("<随机字符>", generate_random_str(6))
            )
            if not os.path.exists(_path := base_path.rsplit("/", 1)[0]):
                os.makedirs(_path, exist_ok=True)
            base_path = base_path.replace("<编号>", str(len(os.listdir(_path))).zfill(5))
            base_path += ".png"
            with open(base_path, "wb") as file:
                file.write(image_data)
            _enforce_storage_budget(Path("./outputs"))
            return base_path
