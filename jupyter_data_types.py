from typing import List
from pydantic import BaseModel, Field

class PromptData(BaseModel):
    """
    Data structure for a single prompt generation request.
    Includes prompt text and generation flags.
    """
    name: str = Field(
        alias="name",
        description="Unique name or identifier for this specific prompt item."
    )
    positive: str = Field(
        alias="pos", 
        description="The main positive prompt describing what to generate."
    )
    negative: str = Field(
        default="", 
        alias="neg", 
        description="The negative prompt describing what to exclude."
    )
    upscale: bool = Field(
        default=False, 
        description="Whether to perform upscaling on the generated image."
    )
    rembg: bool = Field(
        default=False, 
        description="Whether to remove the background from the generated image."
    )
    copy_style: bool = Field(
        default=False, 
        description="Whether to attempt style copying from a reference."
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "pos": "A futuristic city at sunset",
                "upscale": True
            }
        }

class GroupData(BaseModel):
    """
    A group of prompts for batch generation.
    Organizes prompts by group name for folder structuring.
    """
    group_name: str = Field(
        default="unnamed_group", 
        description="Name of the group, used for organization and folder naming."
    )
    prompts: List[PromptData] = Field(
        default_factory=list, 
        description="List of prompts to be processed in this group."
    )

class GroupsConfig(BaseModel):
    """
    Global configuration for batch processing multiple groups.
    This is the root model for parsing JSON inputs.
    """
    groups: List[GroupData] = Field(
        default_factory=list, 
        description="List of prompt groups to process."
    )

class GenItem(BaseModel):
    """
    Internal metadata passed to the generation callback for a single item.
    Used for tracking progress and naming outputs.
    """
    group_name: str
    item_name: str
    group_index: int
    prompt_index: int
    prompt: PromptData
