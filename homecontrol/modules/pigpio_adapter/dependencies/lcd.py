#!/usr/bin/env python

import pigpio
import time


class LCD:
    """
    Commands

    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    Flags for display entry mode

    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    Flags for display on/off control

    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    Flags for display/cursor shift

    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE = 0x00
    LCD_MOVERIGHT = 0x04
    LCD_MOVELEFT = 0x00

    Flags for function set

    LCD_8BITMODE = 0x10
    LCD_4BITMODE = 0x00
    LCD_2LINE = 0x08
    LCD_1LINE = 0x00
    LCD_5x10DOTS = 0x04
    LCD_5x8DOTS = 0x00

    Flags for backlight control

    LCD_BACKLIGHT = 0x08
    LCD_NOBACKLIGHT = 0x00
    """

    _LCD_ROW = [0x80, 0xC0, 0x94, 0xD4]

    def __init__(self, pi, bus=1, addr=0x27, width=16, backlight_on=True):

        self.pi = pi
        self.width = width
        self.backlight_on = backlight_on

        self.RS = (1 << 0)
        self.E = (1 << 2)
        self.BL = (1 << 3)
        self.B4 = 4

        self._h = pi.i2c_open(bus, addr)

        self._init()

    def backlight(self, on):
        """
        Switch backlight on (True) or off (False).
        """
        self.backlight_on = on
        self._data(0x08 if on else 0x00)

    def _init(self):

        self.instruct(0x33)  # Initialise 1
        self.instruct(0x32)  # Initialise 2
        self.instruct(0x06)  # Cursor increment
        self.instruct(0x0C)  # Display on,move_to off, blink off
        self.instruct(0x28)  # 4-bits, 1 line, 5x8 font
        self.instruct(0x01)  # Clear display

    def _byte(self, MSb, LSb):

        if self.backlight_on:
            MSb |= self.BL
            LSb |= self.BL

        self.pi.i2c_write_device(self._h,
                                 [MSb | self.E, MSb & ~self.E, LSb | self.E, LSb & ~self.E])

    def instruct(self, bits):

        MSN = (bits >> 4) & 0x0F
        LSN = bits & 0x0F

        MSb = MSN << self.B4
        LSb = LSN << self.B4

        self._byte(MSb, LSb)

    def _data(self, bits):

        MSN = (bits >> 4) & 0x0F
        LSN = bits & 0x0F

        MSb = (MSN << self.B4) | self.RS
        LSb = (LSN << self.B4) | self.RS

        self._byte(MSb, LSb)

    def move_to(self, row, column):
        """
        Position cursor at row and column (0 based).
        """
        self.instruct(self._LCD_ROW[row] + column)

    def put_symbol(self, index):
        """
        Write the symbol with index at the current cursor postion
        and increment the cursor.
        """
        self._data(index)

    def put_chr(self, char):
        """
        Write a character at the current cursor postion and
        increment the cursor.
        """
        self._data(ord(char))

    def put_str(self, text):
        """
        Write a string at the current cursor postion.  The cursor will
        end up at the character after the end of the string.
        """
        for i in text:
            self.put_chr(i)

    def put_line(self, row, text):
        """
        Replace a row (0 based) of the LCD with a new string.
        """
        text = text.ljust(self.width)[:self.width]

        self.move_to(row, 0)

        self.put_str(text)

    def close(self):
        """
        Close the LCD (clearing the screen) and release used resources.
        """
        try:
            self.instruct(0x01)
        finally:
            self.pi.i2c_close(self._h)
