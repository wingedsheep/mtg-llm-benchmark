"""
Card registry - imports all implemented cards and registers them
"""

from .banishing_light import BanishingLight
# Import spell cards
from .dockworker_drone import DockworkerDrone
from .dual_sun_technique import DualSunTechnique
from .forest import Forest
from .illvoi_galeblade import IllvoiGaleblade
from .island import Island
from .mountain import Mountain
# Import basic lands
from .plains import Plains
from .swamp import Swamp
from ..engine.card_system import card_database


def register_all_cards():
    """Register all cards in the card database"""
    cards_to_register = [
        # Basic lands
        Plains,
        Island,
        Swamp,
        Mountain,
        Forest,

        # Spell cards
        DockworkerDrone,
        DualSunTechnique,
        BanishingLight,
        IllvoiGaleblade
    ]

    for card_class in cards_to_register:
        card_database.register_card(card_class)


# Auto-register when module is imported
register_all_cards()

# Export all card classes for easy importing
__all__ = [
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest',
    'DockworkerDrone', 'DualSunTechnique', 'BanishingLight', 'IllvoiGaleblade'
]
