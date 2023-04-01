import time
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

import pygame


class Layout(ABC):

    def __init__(self, position: Tuple[int, int], size: Tuple[int, int]) -> None:
        super().__init__()

        self.position = position
        self.size = size

    @abstractmethod
    def render(self, screen):
        pass


class FlexboxLayout(Layout):
    def __init__(self, position: Tuple[int, int] = (0, 0), size: Tuple[int, int] = (0, 0), mode: str = 'row',
                 align_items: str = 'start', justify_content: str = 'start',
                 bg_color: Optional[Tuple[int, int, int]] = None):
        super().__init__(position, size)

        self._children: List[Layout] = []
        self._mode = mode
        self._align_items = align_items
        self._justify_content = justify_content
        self._bg_color = bg_color

    def add_child(self, child: Layout):
        self._children.append(child)

    def render(self, screen):
        if self.size[0] == 0 or self.size[1] == 0:
            self._fit_children()

        if self._mode == 'row':
            self._layout_row()
        elif self._mode == 'column':
            self._layout_column()

        if self._bg_color:
            pygame.draw.rect(screen, self._bg_color, (self.position, self.size))

        for child in self._children:
            child.render(screen)

    def _fit_children(self):
        if not self._children:
            return

        if self._mode == 'row':
            self._fit_children_row()
        elif self._mode == 'column':
            self._fit_children_column()

    def _fit_children_row(self):
        total_width = sum(child.size[0] for child in self._children)
        max_height = max(child.size[1] for child in self._children)
        self.size = (total_width, max_height)

    def _fit_children_column(self):
        max_width = max(child.size[0] for child in self._children)
        total_height = sum(child.size[1] for child in self._children)
        self.size = (max_width, total_height)

    def _layout_row(self):
        spacing = 0
        x_offset = self.position[0]
        total_width = sum(child.size[0] for child in self._children)

        if self._justify_content == 'end':
            x_offset += self.size[0] - total_width
        elif self._justify_content == 'center':
            x_offset += (self.size[0] - total_width) / 2
        elif self._justify_content == 'space-between':
            spacing = (self.size[0] - total_width) / (len(self._children) - 1) if len(self._children) > 1 else 0
        elif self._justify_content == 'space-around':
            spacing = (self.size[0] - total_width) / len(self._children) if len(self._children) > 0 else 0
            x_offset += spacing / 2

        for child in self._children:
            y_offset = self.position[1]

            if self._align_items == 'end':
                y_offset += self.size[1] - child.size[1]
            elif self._align_items == 'center':
                y_offset += (self.size[1] - child.size[1]) / 2

            # Set child position
            child.position = (x_offset, y_offset)

            # Update x coordinate for next child
            x_offset += child.size[0] + spacing

    def _layout_column(self):
        spacing = 0
        y_offset = self.position[1]
        total_height = sum(child.size[1] for child in self._children)

        if self._justify_content == 'end':
            y_offset += self.size[1] - total_height
        elif self._justify_content == 'center':
            y_offset += (self.size[1] - total_height) / 2
        elif self._justify_content == 'space-between':
            spacing = (self.size[1] - total_height) / (len(self._children) - 1) if len(self._children) > 1 else 0
        elif self._justify_content == 'space-around':
            spacing = (self.size[1] - total_height) / len(self._children) if len(self._children) > 0 else 0
            y_offset += spacing / 2

        for child in self._children:
            x_offset = self.position[0]

            if self._align_items == 'end':
                x_offset += self.size[0] - child.size[0]
            elif self._align_items == 'center':
                x_offset += (self.size[0] - child.size[0]) / 2

            # Set child position
            child.position = (x_offset, y_offset)

            # Update y coordinate for next child
            y_offset += child.size[1] + spacing


class TextLayout(Layout):
    def __init__(self, text: str,
                 font: pygame.font.Font = None, font_size=16, color: Tuple[int, int, int] = (255, 255, 255),
                 position: Tuple[int, int] = (0, 0)):
        self._text = text
        self._font = font or pygame.font.Font(None, font_size)
        self._color = color
        self._surface = self._font.render(self._text, True, self._color)

        super().__init__(position, (self._surface.get_width(), self._surface.get_height()))

    def render(self, screen):
        screen.blit(self._surface, self.position)


class ThreeDotsTextLayout(TextLayout):
    _dots = ""
    _last_time = time.time()

    def __init__(self, text: str, font: pygame.font.Font = None, font_size=16,
                 color: Tuple[int, int, int] = (255, 255, 255), position: Tuple[int, int] = (0, 0)):
        super().__init__(text, font, font_size, color, position)

    def render(self, screen):
        if (time.time() - ThreeDotsTextLayout._last_time) > 1:
            ThreeDotsTextLayout._last_time = time.time()
            ThreeDotsTextLayout._dots += "."
            if len(ThreeDotsTextLayout._dots) > 3:
                ThreeDotsTextLayout._dots = ""
        self._surface = self._font.render(f"{self._text}{ThreeDotsTextLayout._dots}", True, self._color)
        super().render(screen)


class MouseCoordinates:
    def __init__(self, font_size: int = 20, color: Tuple[int, int, int] = (255, 255, 255)):
        self.font = pygame.font.Font(None, font_size)
        self.color = color

    def render(self, screen: pygame.Surface):
        # Get the mouse position
        x, y = pygame.mouse.get_pos()

        # Render the mouse coordinates as text
        coord_text = self.font.render(f"({x}, {y})", True, self.color)

        # Draw the text on the screen at the mouse position
        screen.blit(coord_text, (x, y))
