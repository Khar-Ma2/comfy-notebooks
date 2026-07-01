import PIL.Image
from pathlib import Path
from typing import Callable, Any, Iterator
from jupyter_data_types import GroupsConfig, GenItem

def save_img(image: PIL.Image.Image, path: Path) -> None:
    """
    Saves a PIL image to the specified path as a PNG.
    Strips all metadata, sets 300 DPI, and preserves the alpha channel.
    
    Args:
        image: The PIL image object to save.
        path: Destination file path.
    """
    clean = PIL.Image.new(image.mode, image.size)
    clean.paste(image)
    clean.save(path, format="PNG", dpi=(300, 300), compress_level=1)

def work_with(
    config: GroupsConfig, 
    action_callback: Callable[[GenItem], Any]
) -> Iterator[Callable[[], Any]]:
    """
    Iterates through the Pydantic configuration and yields sequential callbacks.
    The actual generation and preview logic should be provided inside the action_callback.
    
    Args:
        config: The parsed Pydantic model containing groups and prompts.
        action_callback: A callback function (usually a lambda) that takes a GenItem.
        
    Yields:
        A callable that, when executed, triggers the action_callback for the next prompt.
    """
    for g_idx, group in enumerate(config.groups):
        for p_idx, prompt_data in enumerate(group.prompts):
            if not prompt_data.positive:
                continue

            # Generate item name from prompt name if available, otherwise use index
            # (Note: name was added to PromptData in previous user edit)
            
            # Aggregate metadata for the generation task
            item = GenItem(
                group_name=group.group_name,
                item_name=prompt_data.name,
                group_index=g_idx,
                prompt_index=p_idx,
                prompt=prompt_data
            )

            # Yield a sequential callback
            yield lambda it=item: action_callback(it)
