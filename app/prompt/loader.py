"""提示词模板加载器。

提供从项目根目录 prompts/ 目录读取 .prompt 提示词模板文件的能力，
供 Agent 各节点构建 LLM 对话时复用。
"""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def load_prompt(prompt_name: str) -> str:
    """按名称加载提示词模板。

    模板内容在首次读取后进程内缓存，运行期间修改模板文件不会生效。

    Args:
        prompt_name: 提示词文件名（不含 .prompt 扩展名），如 "nl2sql"。

    Returns:
        提示词文件的完整文本内容（UTF-8 编码）。

    Raises:
        ValueError: prompt_name 为空或不是纯文件名时抛出。
        FileNotFoundError: prompts/ 目录或对应的提示词文件不存在时抛出。
    """
    # 仅允许纯文件名：拦截空串、路径分隔符与 "."、".."，
    # 避免借名称读取仓库内任意文件。
    if (
        not prompt_name
        or "/" in prompt_name
        or "\\" in prompt_name
        or prompt_name in {".", ".."}
    ):
        raise ValueError(f"非法的提示词名称：{prompt_name!r}")

    # 以本文件为基准向上三级定位项目根目录（app/prompt/loader.py -> 项目根），
    # 保证应用从任意工作目录启动时均能找到提示词目录。
    prompt_path = Path(__file__).parents[2] / "prompts" / f"{prompt_name}.prompt"
    return prompt_path.read_text(encoding="utf-8")
