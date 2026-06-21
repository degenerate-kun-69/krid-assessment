"""
app/models/tenant.py — Pydantic model for a Tenant (Company).
Each tenant has a system prompt and a media library mapping
keyword → public URL (image or PDF).
"""

from pydantic import BaseModel, Field
from typing import Dict


class Tenant(BaseModel):
    tenant_id: str = Field(..., description="Unique identifier, e.g. 'tenant_a'")
    name: str = Field(..., description="Display name, e.g. 'Luxury Furniture Store'")
    system_prompt: str = Field(
        ...,
        description=(
            "System instructions given to the LLM. Describes the brand's "
            "tone, products, and how to handle customer queries."
        ),
    )
    media_library: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Mapping of keyword → public URL. "
            "Example: {'catalog': 'https://example.com/catalog.pdf', "
            "'sofa': 'https://example.com/sofa.jpg'}"
        ),
    )
