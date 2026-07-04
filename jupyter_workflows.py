import PIL.Image
from comfy_script.runtime import *
from comfy_script.runtime.nodes import *


async def flux1_img_gen(
    prompt: str,
    flux_model: UNETs | str,
    flux_vae: VAEs | str,
    clip1: DualCLIPLoader.clip_name1 | str,
    clip2: DualCLIPLoader.clip_name2 | str,
    noise: int,
    guidance: float,
    weight_dtype: UNETLoader.weight_dtype | str,
    ksampler: Samplers | str,
    max_shift: float,
    base_shift: float,
    scheduler: Schedulers | str,
    steps: int,
    denoise: float,
    latent_width: int = 1024,
    latent_height: int = 1024,
    batch_size: int = 1,
    clip_type: DualCLIPLoader.type | str = DualCLIPLoader.type.flux,
    clip_device: DualCLIPLoader.device | str = DualCLIPLoader.device.default,
) -> PIL.Image.Image | None:
    """
    Executes the Flux image generation workflow using comfy-script.

    Args:
        prompt: Positive text prompt.
        flux_model: Name or object of the Flux UNET model.
        flux_vae: Name or object of the Flux VAE.
        clip1: Name of the first CLIP model (e.g. t5).
        clip2: Name of the second CLIP model (e.g. clip-l).
        noise: Random seed for noise generation.
        guidance: Guidance scale for Flux.
        weight_dtype: Data type for weights (fp8, bf16, etc.).
        ksampler: Sampler name.
        max_shift: Flux sampling max shift.
        base_shift: Flux sampling base shift.
        scheduler: Scheduler name.
        steps: Number of sampling steps.
        denoise: Denoising strength (0.0 to 1.0).
        latent_width: Width of the output image.
        latent_height: Height of the output image.
        batch_size: Number of images to generate in a batch.
        clip_type: Type of CLIP loader.
        clip_device: Device to run CLIP on.

    Returns:
        The first generated image as a PIL.Image.Image object, or None if generation failed.
    """
    with Workflow():
        # Setup noise and models
        noise_node = RandomNoise(noise)
        model = UNETLoader(flux_model, weight_dtype)
        clip = DualCLIPLoader(clip1, clip2, clip_type, clip_device)

        # Conditioning and Guidance
        conditioning = CLIPTextEncode(prompt, clip)
        conditioning = FluxGuidance(conditioning, guidance)
        guider = BasicGuider(model, conditioning)

        # Sampling configuration
        sampler = KSamplerSelect(ksampler)
        model_sampling = ModelSamplingFlux(
            model, max_shift, base_shift, latent_width, latent_height
        )
        sigmas = BasicScheduler(model_sampling, scheduler, steps, denoise)

        # Latent and Generation
        latent = EmptyLatentImage(latent_width, latent_height, batch_size)
        latent, _ = SamplerCustomAdvanced(noise_node, guider, sampler, sigmas, latent)

        # VAE Decode
        vae = VAELoader(flux_vae)
        image = VAEDecode(latent, vae)

        # Retrieve results
        images_pil = util.get_images(image)
        return images_pil[0] if images_pil else None
