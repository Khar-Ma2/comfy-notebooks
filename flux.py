# %% [markdown]
#  # 1. Imports & Setup
#
#  In this cell, we import all required modules and connect to ComfyUI.

# %%
import asyncio
import json
import random
from pathlib import Path
from IPython.display import clear_output, display

# ComfyScript imports
import comfy_script.ui as ui
from comfy_script.runtime import Workflow
from comfy_script.runtime import *
from comfy_script.runtime.nodes import *

# Connect to ComfyUI
load("http://127.0.0.1:8188/")
# load("/workspace/ComfyUI/")

# Import our custom modules
from jupyter_data_types import GroupsConfig, GenItem
from jupyter_utils import work_with, save_img
from jupyter_workflows import flux1_img_gen


# %% [markdown]
#  # 2. Load Workload (JSON)
#
#  Load JSON with groups and prompts. The data is parsed via Pydantic.

# %%
WORKLOAD_FILE_PATH = Path("../flux_workload.json")
with open(WORKLOAD_FILE_PATH, "r", encoding="utf-8") as f:
    JSON_PAYLOAD = f.read()

# Parsing and saving as a global variable
WORKLOAD_CONFIG = GroupsConfig.model_validate_json(JSON_PAYLOAD)
print(f"Loaded {len(WORKLOAD_CONFIG.groups)} groups.")
prompts = 0
for g in WORKLOAD_CONFIG.groups:
    prompts += len(g.prompts)

print(f"Loaded {prompts} prompts.")

# %% [markdown]
#  # 3. Global Generation Parameters
#
#  Global variables that will be passed to flux_img_gen.

# %%
get_seed = lambda: random.randint(0, 1000000)
SEED = -1  # -1 for generate seed
FLUX_MODEL = "flux1-schnell.safetensors"
FLUX_VAE = "flux_v1_vae.safetensors"
CLIP1 = "clip_l.safetensors"
# CLIP1 = "t5xxl_fp8_e4m3fn.safetensors"
CLIP2 = "t5xxl_fp16.safetensors"
# CLIP1 = "t5xxl_fp16.safetensors"
GUIDANCE = 1
WEIGHT_DTYPE = "fp8_e4m3fn"
KSAMPLER = "euler"
MAX_SHIFT = 1.15
BASE_SHIFT = 0.5
SCHEDULER = "simple"
STEPS = 4
DENOISE = 1.0
LATENT_WIDTH = 1024
LATENT_HEIGHT = 1024
BATCH_SIZE = 1

OUTPUT_DIR = Path("/workspace/export/flux-prompts-fp16/")


# %% [markdown]
#  # 4. Generation Worker Setup & Execution
#
#  In this cell, we define the `GenerationWorker` class which coordinates running the generation
#  workload as a background asyncio task. It tracks progress and state, notifying any registered listeners.

# %%
import io
import asyncio
import ipywidgets as widgets
from IPython.display import display
import random


class GenerationWorker:
    def __init__(self, config, params):
        self.config = config
        self.params = params
        self.current_group = None
        self.group_images = []
        self.group_titles = []
        self.total_generated_globally = 0
        self.total_groups = len(config.groups)
        self.total_prompts = sum(len(g.prompts) for g in config.groups)

        self.current_item = None
        self.status = "Idle"  # Idle, Running, Completed, Cancelled, Failed
        self.error = None
        self._listeners = []
        self._task = None

    def register_listener(self, listener):
        self._listeners.append(listener)
        # Call it immediately so the listener has the current state
        listener(self)

    def unregister_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self):
        for listener in list(self._listeners):
            try:
                listener(self)
            except Exception:
                # Remove stale listeners that failed
                self._listeners.remove(listener)

    def start(self):
        if self._task and not self._task.done():
            print("Worker is already running!")
            return
        self.status = "Running"
        self._task = asyncio.create_task(self.run())
        print("Generation worker started in the background.")

    def cancel(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self.status = "Cancelled"
            self._notify()
            print("Generation worker cancellation requested.")

    async def run(self):
        try:
            callbacks = work_with(self.config, self.process_item)
            for cb in callbacks:
                await cb()
            self.status = "Completed"
        except asyncio.CancelledError:
            self.status = "Cancelled"
        except Exception as e:
            self.status = "Failed"
            self.error = str(e)
            print(f"Error in generation worker: {e}")
        finally:
            self._notify()

    async def process_item(self, item: GenItem):
        self.current_item = item
        prompts_in_group = len(self.config.groups[item.group_index].prompts)

        if self.current_group != item.group_name:
            self.current_group = item.group_name
            self.group_images = []
            self.group_titles = []

        self._notify()

        img = await flux1_img_gen(
            prompt=item.prompt.positive,
            flux_model=self.params["FLUX_MODEL"],
            flux_vae=self.params["FLUX_VAE"],
            clip1=self.params["CLIP1"],
            clip2=self.params["CLIP2"],
            noise=self.params["SEED"] if self.params["SEED"] != -1 else get_seed(),
            guidance=self.params["GUIDANCE"],
            weight_dtype=self.params["WEIGHT_DTYPE"],
            ksampler=self.params["KSAMPLER"],
            max_shift=self.params["MAX_SHIFT"],
            base_shift=self.params["BASE_SHIFT"],
            scheduler=self.params["SCHEDULER"],
            steps=self.params["STEPS"],
            denoise=self.params["DENOISE"],
            latent_width=self.params["LATENT_WIDTH"],
            latent_height=self.params["LATENT_HEIGHT"],
            batch_size=self.params["BATCH_SIZE"],
        )

        if img:
            save_path = (
                self.params["OUTPUT_DIR"] / item.group_name / f"{item.item_name}.png"
            )
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_img(img, save_path)

            self.total_generated_globally += 1
            self.group_images.append(img)
            self.group_titles.append(item.item_name)
            self._notify()


# Gather generation parameters into a dictionary
PARAMS = {
    "FLUX_MODEL": FLUX_MODEL,
    "FLUX_VAE": FLUX_VAE,
    "CLIP1": CLIP1,
    "CLIP2": CLIP2,
    "SEED": SEED,
    "GUIDANCE": GUIDANCE,
    "WEIGHT_DTYPE": WEIGHT_DTYPE,
    "KSAMPLER": KSAMPLER,
    "MAX_SHIFT": MAX_SHIFT,
    "BASE_SHIFT": BASE_SHIFT,
    "SCHEDULER": SCHEDULER,
    "STEPS": STEPS,
    "DENOISE": DENOISE,
    "LATENT_WIDTH": LATENT_WIDTH,
    "LATENT_HEIGHT": LATENT_HEIGHT,
    "BATCH_SIZE": BATCH_SIZE,
    "OUTPUT_DIR": OUTPUT_DIR,
}

# Instantiate and start the worker if not already running
if "generation_worker" not in globals() or generation_worker.status in [
    "Completed",
    "Cancelled",
    "Failed",
    "Idle",
]:
    generation_worker = GenerationWorker(WORKLOAD_CONFIG, PARAMS)
    generation_worker.start()
else:
    print("Worker is already running in background.")


# %% [markdown]
#  # 5. UI Monitor
#
#  Displays the interactive UI to monitor progress and show generated images.
#  You can safely re-run this cell to reconnect the UI.

# %%
if "generation_worker" in globals():
    # Output widgets
    grid_output = widgets.Output()
    status_output = widgets.Output()

    # Cancel button
    cancel_btn = widgets.Button(
        description="Cancel Generation",
        button_style="danger",
        tooltip="Click to abort the current generation queue",
        icon="stop",
    )

    def on_cancel_clicked(b):
        generation_worker.cancel()
        cancel_btn.disabled = True

    cancel_btn.on_click(on_cancel_clicked)

    # Display layout
    display(
        widgets.VBox(
            [
                widgets.HBox([cancel_btn], layout=widgets.Layout(margin="10px 0px")),
                grid_output,
                widgets.HTML("<hr style='border: 1px solid #30363d; margin: 15px 0;'>"),
                status_output,
            ]
        )
    )

    def render_image_grid(images, titles):
        """Generates a clean adaptive grid of images using native ipywidgets."""
        grid_items = []
        for img, title in zip(images, titles):
            byte_arr = io.BytesIO()
            img.save(byte_arr, format="PNG")
            img_bytes = byte_arr.getvalue()

            img_widget = widgets.Image(
                value=img_bytes,
                format="png",
                layout=widgets.Layout(
                    width="100%",
                    max_width="250px",
                    border="1px solid #30363d",
                    border_radius="4px",
                ),
            )
            lbl_widget = widgets.Label(
                value=title,
                layout=widgets.Layout(
                    display="flex", justify_content="center", font_weight="bold"
                ),
            )

            grid_items.append(
                widgets.VBox(
                    [img_widget, lbl_widget],
                    layout=widgets.Layout(align_items="center"),
                )
            )

        return widgets.GridBox(
            grid_items,
            layout=widgets.Layout(
                grid_template_columns="repeat(auto-fill, minmax(220px, 1fr))",
                grid_gap="15px",
                width="100%",
            ),
        )

    def update_ui(worker):
        # Update cancel button state
        if worker.status in ["Completed", "Cancelled", "Failed"]:
            cancel_btn.disabled = True
        else:
            cancel_btn.disabled = False

        # 1. Update Grid Box
        with grid_output:
            grid_output.clear_output(wait=True)
            if worker.group_images:
                display(render_image_grid(worker.group_images, worker.group_titles))
            else:
                print("No images generated in the current group yet.")

        # 2. Update Status Box
        with status_output:
            status_output.clear_output(wait=True)
            print("📊 СТАН ГЕНЕРАЦІЇ:")
            print(f"Статус воркера: {worker.status}")
            if worker.error:
                print(f"❌ Помилка: {worker.error}")

            print(
                f"Загальний прогрес: груп {worker.total_groups} | картинок {worker.total_generated_globally}/{worker.total_prompts}"
            )

            if worker.current_item:
                item = worker.current_item
                prompts_in_group = len(worker.config.groups[item.group_index].prompts)
                print(
                    f"Група: {item.group_index + 1}/{worker.total_groups} ({item.group_name})"
                )
                print(
                    f"Зображення в групі: {item.prompt_index + 1}/{prompts_in_group} ({item.item_name})"
                )
                print(f"Промпт: {item.prompt.positive}")

    # Remove previous listener if it exists to avoid duplicate UI updates
    if "current_ui_listener" in globals():
        generation_worker.unregister_listener(current_ui_listener)

    current_ui_listener = update_ui
    generation_worker.register_listener(current_ui_listener)
else:
    print("Worker is not initialized. Please run the setup cell above.")
