import pygame


class TextBoxLayout:
    ALIGNMENTS = {
        "topleft": lambda box_rect, text_rect: (box_rect.left, box_rect.top),
        "topcenter": lambda box_rect, text_rect: (box_rect.centerx - text_rect.width // 2, box_rect.top),
        "topright": lambda box_rect, text_rect: (box_rect.right - text_rect.width, box_rect.top),
        "centerleft": lambda box_rect, text_rect: (box_rect.left, box_rect.centery - text_rect.height // 2),
        "centerright": lambda box_rect, text_rect: (
            box_rect.right - text_rect.width, box_rect.centery - text_rect.height // 2),
        "center": lambda box_rect, text_rect: (
            box_rect.centerx - text_rect.width // 2, box_rect.centery - text_rect.height // 2),
        "bottomleft": lambda box_rect, text_rect: (box_rect.left, box_rect.bottom - text_rect.height),
        "bottomcenter": lambda box_rect, text_rect: (
            box_rect.centerx - text_rect.width // 2, box_rect.bottom - text_rect.height),
        "bottomright": lambda box_rect, text_rect: (
            box_rect.right - text_rect.width, box_rect.bottom - text_rect.height),
    }

    def __init__(self,
                 surface,
                 x: int,
                 y: int,
                 width=None,
                 height=None,
                 align="topleft",
                 font=None,
                 font_size=20,
                 line_spacing=4,
                 margin=10):
        self._surface = surface
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._align = align
        self._font = font or pygame.font.Font(None, font_size)
        self._line_spacing = line_spacing
        self._margin = margin
        self._lines = []

    def _fit_text_to_box(self):
        max_width = 0
        total_height = 0
        for line in self._lines:
            text_surface = self._font.render(line.text, True, line.color)
            max_width = max(max_width, text_surface.get_width())
            total_height += text_surface.get_height() + self._line_spacing
        total_height -= self._line_spacing

        if self._width is None:
            self._width = max_width + 2 * self._margin
        if self._height is None:
            self._height = total_height + 2 * self._margin

        x, y = self.ALIGNMENTS[self._align](pygame.Rect(self._x, self._y, self._width, self._height),
                                            pygame.Rect(0, 0, max_width, total_height))
        y += self._margin

        for line in self._lines:
            text_surface = self._font.render(line.text, True, line.color)
            line.rect = text_surface.get_rect(topleft=(x, y))
            y += text_surface.get_height() + self._line_spacing

    def add_line(self, text, color=(255, 255, 255)):
        self._lines.append(Line(text, color))

    def render(self):
        self._fit_text_to_box()
        for line in self._lines:
            self._surface.blit(self._font.render(line.text, True, line.color), line.rect)


class Line:
    def __init__(self, text, color):
        self.text = text
        self.color = color
        self.rect = None
