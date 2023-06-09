import pygame

KEY_MAPPING = {
    pygame.K_BACKSPACE: 'backspace',
    pygame.K_TAB: 'tab',
    pygame.K_RETURN: 'enter',
    pygame.K_ESCAPE: 'esc',
    pygame.K_SPACE: 'space',
    pygame.K_EXCLAIM: '!',
    pygame.K_QUOTEDBL: '"',
    pygame.K_HASH: '#',
    pygame.K_DOLLAR: '$',
    pygame.K_AMPERSAND: '&',
    pygame.K_QUOTE: "'",
    pygame.K_LEFTPAREN: '(',
    pygame.K_RIGHTPAREN: ')',
    pygame.K_ASTERISK: '*',
    pygame.K_PLUS: '+',
    pygame.K_MINUS: '-',
    pygame.K_PERIOD: '.',
    pygame.K_SLASH: '/',
    pygame.K_0: '0',
    pygame.K_1: '1',
    pygame.K_2: '2',
    pygame.K_3: '3',
    pygame.K_4: '4',
    pygame.K_5: '5',
    pygame.K_6: '6',
    pygame.K_7: '7',
    pygame.K_8: '8',
    pygame.K_9: '9',
    pygame.K_COLON: ':',
    pygame.K_SEMICOLON: ';',
    pygame.K_LESS: '<',
    pygame.K_EQUALS: '=',
    pygame.K_GREATER: '>',
    pygame.K_QUESTION: '?',
    pygame.K_AT: '@',
    pygame.K_LEFTBRACKET: '[',
    pygame.K_BACKSLASH: '\\',
    pygame.K_RIGHTBRACKET: ']',
    pygame.K_CARET: '^',
    pygame.K_UNDERSCORE: '_',
    pygame.K_BACKQUOTE: '`',
    pygame.K_a: 'a',
    pygame.K_b: 'b',
    pygame.K_c: 'c',
    pygame.K_d: 'd',
    pygame.K_e: 'e',
    pygame.K_f: 'f',
    pygame.K_g: 'g',
    pygame.K_h: 'h',
    pygame.K_i: 'i',
    pygame.K_j: 'j',
    pygame.K_k: 'k',
    pygame.K_l: 'l',
    pygame.K_m: 'm',
    pygame.K_n: 'n',
    pygame.K_o: 'o',
    pygame.K_p: 'p',
    pygame.K_q: 'q',
    pygame.K_r: 'r',
    pygame.K_s: 's',
    pygame.K_t: 't',
    pygame.K_u: 'u',
    pygame.K_v: 'v',
    pygame.K_w: 'w',
    pygame.K_x: 'x',
    pygame.K_y: 'y',
    pygame.K_z: 'z',
    pygame.K_DELETE: 'delete',
    pygame.K_KP0: 'num0',
    pygame.K_KP1: 'num1',
    pygame.K_KP2: 'num2',
    pygame.K_KP3: 'num3',
    pygame.K_KP4: 'num4',
    pygame.K_KP5: 'num5',
    pygame.K_KP6: 'num6',
    pygame.K_KP7: 'num7',
    pygame.K_KP8: 'num8',
    pygame.K_KP9: 'num9',
    pygame.K_KP_PERIOD: 'num.',
    pygame.K_KP_DIVIDE: 'num/',
    pygame.K_KP_MULTIPLY: 'num*',
    pygame.K_KP_MINUS: 'num-',
    pygame.K_KP_PLUS: 'num+',
    pygame.K_KP_ENTER: 'numenter',
    pygame.K_UP: 'up',
    pygame.K_DOWN: 'down',
    pygame.K_LEFT: 'left',
    pygame.K_RIGHT: 'right',
    pygame.K_INSERT: 'insert',
    pygame.K_HOME: 'home',
    pygame.K_END: 'end',
    pygame.K_PAGEUP: 'pageup',
    pygame.K_PAGEDOWN: 'pagedown',
    pygame.K_F1: 'f1',
    pygame.K_F2: 'f2',
    pygame.K_F3: 'f3',
    pygame.K_F4: 'f4',
    pygame.K_F5: 'f5',
    pygame.K_F6: 'f6',
    pygame.K_F7: 'f7',
    pygame.K_F8: 'f8',
    pygame.K_F9: 'f9',
    pygame.K_F10: 'f10',
    pygame.K_F11: 'f11',
    pygame.K_F12: 'f12',
    pygame.K_NUMLOCK: 'numlock',
    pygame.K_CAPSLOCK: 'capslock',
    pygame.K_SCROLLOCK: 'scrolllock',
    pygame.K_RSHIFT: 'shift',
    pygame.K_LSHIFT: 'shiftleft',
    pygame.K_RCTRL: 'ctrl',
    pygame.K_LCTRL: 'ctrlleft',
    pygame.K_RALT: 'alt',
    pygame.K_LALT: 'altleft',
    pygame.K_LMETA: 'leftmeta',
    pygame.K_RMETA: 'rightmeta',
    pygame.K_LSUPER: 'leftsuper',  # left windows key
    pygame.K_RSUPER: 'rightsuper',  # right windows key
    pygame.K_MODE: 'mode',
    pygame.K_HELP: 'help',
    pygame.K_PRINT: 'printscreen',
    pygame.K_SYSREQ: 'sysreq',
    pygame.K_BREAK: 'break',
    pygame.K_MENU: 'menu',
    pygame.K_POWER: 'power',
    pygame.K_EURO: 'euro',
}
