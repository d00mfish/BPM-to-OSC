#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SevenSegmentDisplay vs. 0.1 (2020)
#
# Written by E. A. Tacao <mailto@tacao.com.br>, (C) 2020
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     (1) Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#     (2) Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#
#     (3)The name of the author may not be used to
#     endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#


import wx, math

#-------------------------------------------------------------------------------

_opts = {"0" : "1111110",
         "1" : "0110000",
         "2" : "1101101",
         "3" : "1111001",
         "4" : "0110011",
         "5" : "1011011",
         "6" : "1011111",
         "7" : "1110000",
         "8" : "1111111",
         "9" : "1111011",
         "A" : "1110111",
         "B" : "0011111",
         "C" : "1001110",
         "D" : "0111101",
         "E" : "1001111",
         "F" : "1000111",
         "-" : "0000001",
         " " : "0000000",
         "R" : "0000101",
         "O" : "0011101",
         "H" : "0110111",
         "L" : "0001110",
         "P" : "1100111",
         "°" : "1100011"}

_elms = ["A", "B", "C", "D", "E", "F", "G", "Dot", "Colon"]

#-------------------------------------------------------------------------------

class SevenSegmentDisp(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.parent = parent
        self.drawing_params = None
        self.mysize = self.GetSize()

        self.SetValue("8.:")

        self.thickness    = 10
        self.rwidth       = 38
        self.rheight      = 38
        self.radius       = self.thickness
        self.sep          = 3
        self.tilt         = 10 # degrees
        self.margin       = wx.Point(2, 2)
        self.enable_dot   = True
        self.enable_colon = True

        self.colours = type("colours", (), {})
        self.colours.background = wx.Colour(0, 0, 0, 255)
        self.colours.pen_seg_on = wx.Colour(1, 196, 196, 255)
        self.colours.brush_seg_on = wx.Colour(0, 196, 196, 255)
        self.colours.pen_seg_off = wx.Colour(0, 33, 33, 255)
        self.colours.brush_seg_off = wx.Colour(0, 33, 33, 255)

        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)


    def OnSize(self, evt):
        if self.GetClientSize() != self.mysize:
            self.mysize = self.GetClientSize()
            self.InitBuffer()
        evt.Skip()


    def InitBuffer(self):
        sz = self.GetClientSize()
        sz.width = max(1, sz.width)
        sz.height = max(1, sz.height)
        self._buffer = wx.Bitmap(sz.width, sz.height, 32)
        dc = wx.MemoryDC(self._buffer)
        gc = wx.GCDC(dc)
        self.Calc(gc)


    def Calc(self, dc):
        dc.SetAxisOrientation(True, False)
        gc = dc.GraphicsContext
        path = gc.CreatePath()

        spaths = []

        for s in _elms:
            fn = getattr(self, "GetPath"+s)
            spath = fn(gc)
            path.AddPath(spath)
            spaths.append(spath)

        # tilt
        m = gc.GetTransform()
        m.Set(c=-math.tan(math.radians(self.tilt)))
        path.Transform(m)
        m1 = m

        sw, sh = self.GetSize()
        xm, ym = self.margin
        sw = sw-xm*2; sh = sh-ym*2
        bx, by, bw, bh = path.GetBox()

        # resize
        p = min(sw/bw, sh/bh)
        m = gc.GetTransform()
        m.Set(a=p, d=p)
        path.Transform(m)
        m2 = m

        bx, by, bw, bh = path.GetBox()

        # centre
        x = (sw-bw)/2 - bx + xm
        y = (sh-bh)/2 - by + ym

        m = gc.GetTransform()
        m.Set(tx=x, ty=y)
        path.Transform(m)
        m3 = m

        self.drawing_params = (spaths, p, m1, m2, m3)


    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self, self._buffer)
        gc = wx.GCDC(dc)
        self.Draw(gc)


    def GetElements(self):
        dot = False; colon = False

        if len(self.value) == 1:
            value = self.value
        else:
            value = self.value[0]
            if "." in self.value:
                 dot = True
            if ":" in self.value:
                 colon = True

        return value, dot, colon


    def Draw(self, dc):
        dc.SetBackground(wx.Brush(self.colours.background))
        dc.Clear()
        dc.SetAxisOrientation(True, False)

        gc = dc.GraphicsContext
        spaths, p, m1, m2, m3 = self.drawing_params

        path_on  = gc.CreatePath()
        path_off = gc.CreatePath()

        value, dot, colon = self.GetElements()

        segments = _opts.get(value, _opts[" "])
        for i in range(0, 7):
            if int(segments[i]) == 1:
                path_on.AddPath(spaths[i])
            else:
                path_off.AddPath(spaths[i])

        for m in (m1, m2, m3):
            path_on.Transform(m)
            path_off.Transform(m)

        gc.SetPen(wx.Pen(self.colours.pen_seg_on))
        gc.SetBrush(wx.Brush(self.colours.brush_seg_on))
        gc.DrawPath(path_on)

        gc.SetPen(wx.Pen(self.colours.pen_seg_off))
        gc.SetBrush(wx.Brush(self.colours.brush_seg_off))
        gc.DrawPath(path_off)

        if self.enable_dot:
            dpath = gc.CreatePath()
            dpath.MoveToPoint(self.rwidth+self.sep+self.thickness*2,
                              self.rheight*2+self.thickness*1.5+self.sep*4)
            for m in (m1, m2, m3):
                dpath.Transform(m)
            x, y = dpath.GetCurrentPoint()
            dpath.AddCircle(x, y, p*self.thickness/2)

            if dot:
                gc.SetPen(wx.Pen(self.colours.pen_seg_on))
                gc.SetBrush(wx.Brush(self.colours.brush_seg_on))
            else:
                gc.SetPen(wx.Pen(self.colours.pen_seg_off))
                gc.SetBrush(wx.Brush(self.colours.brush_seg_off))

            gc.DrawPath(dpath)

        if self.enable_colon:
            c1path = gc.CreatePath()
            c1path.MoveToPoint(self.rwidth+self.sep+self.thickness*2.5,
                               self.rheight-self.thickness*0.5+self.sep)
            for m in (m1, m2, m3):
                c1path.Transform(m)
            x, y = c1path.GetCurrentPoint()
            c1path.AddCircle(x, y, p*self.thickness/3)

            c2path = gc.CreatePath()
            c2path.MoveToPoint(self.rwidth+self.sep+self.thickness*2.5,
                               self.rheight+self.thickness*2+self.sep*3)
            for m in (m1, m2, m3):
                c2path.Transform(m)
            x, y = c2path.GetCurrentPoint()
            c2path.AddCircle(x, y, p*self.thickness/3)

            if colon:
                gc.SetPen(wx.Pen(self.colours.pen_seg_on))
                gc.SetBrush(wx.Brush(self.colours.brush_seg_on))
            else:
                gc.SetPen(wx.Pen(self.colours.pen_seg_off))
                gc.SetBrush(wx.Brush(self.colours.brush_seg_off))

            gc.DrawPath(c1path)
            gc.DrawPath(c2path)


    def GetPathA(self, gc):
        path = gc.CreatePath()
        path.AddArc(0, 0, self.radius, -math.radians(135),
                    -math.radians(90), True)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x+self.rwidth, y)
        path.AddArc(self.rwidth, 0, self.radius, -math.radians(90),
                    -math.radians(45), True)
        path.AddLineToPoint(self.rwidth, 0)
        path.AddLineToPoint(0, 0)
        path.CloseSubpath()
        return path


    def GetPathB(self, gc):
        path = gc.CreatePath()
        path.AddArc(self.rwidth+self.sep, 0+self.sep, self.radius,
                    -math.radians(45), -math.radians(0), True)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x, y+self.rheight)
        path.AddLineToPoint(x-self.thickness/2, y+self.rheight+self.thickness/2)
        path.AddLineToPoint(x-self.thickness, y+self.rheight)
        path.AddLineToPoint(x-self.thickness, y)
        path.CloseSubpath()
        return path


    def GetPathC(self, gc):
        path = gc.CreatePath()
        path.MoveToPoint(self.rwidth+self.sep,
                         self.rheight+self.thickness+self.sep*3)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x+self.thickness/2, y-self.thickness/2)
        path.AddLineToPoint(x+self.thickness, y)
        path.AddLineToPoint(x+self.thickness, y+self.rheight)
        path.AddArc(x, y+self.rheight, self.radius, -math.radians(0),
                    -math.radians(-45), True)
        path.AddLineToPoint(x, y+self.rheight)
        path.CloseSubpath()
        return path


    def GetPathD(self, gc):
        path = gc.CreatePath()
        path.AddArc(0, self.rheight*2+self.thickness+self.sep*4, self.radius,
                    -math.radians(225), -math.radians(270), False)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x+self.rwidth, y)
        path.AddArc(x+self.rwidth, y-self.thickness, self.radius,
                    -math.radians(270), -math.radians(315), False)
        path.AddLineToPoint(x+self.rwidth, y-self.thickness)
        path.AddLineToPoint(x, y-self.thickness)
        path.CloseSubpath()
        return path


    def GetPathE(self, gc):
        path = gc.CreatePath()
        path.MoveToPoint(0-self.thickness-self.sep,
                         self.rheight+self.thickness+self.sep*3)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x+self.thickness/2, y-self.thickness/2)
        path.AddLineToPoint(x+self.thickness, y)
        path.AddLineToPoint(x+self.thickness, y+self.rheight)
        path.AddArc(x+self.thickness, y+self.rheight, self.radius,
                    -math.radians(225), -math.radians(180), True)
        path.AddLineToPoint(x, y+self.rheight)
        path.CloseSubpath()
        return path


    def GetPathF(self, gc):
        path = gc.CreatePath()
        path.AddArc(0-self.sep, 0+self.sep, self.radius, -math.radians(135),
                    -math.radians(180), False)
        path.AddLineToPoint(0-self.thickness-self.sep, self.rheight+self.sep)
        x, y = path.GetCurrentPoint()
        path.AddLineToPoint(x+self.thickness/2, y+self.thickness/2)
        path.AddLineToPoint(x+self.thickness, y)
        path.AddLineToPoint(x+self.thickness, self.sep)
        path.CloseSubpath()
        return path


    def GetPathG(self, gc):
        path = gc.CreatePath()
        path.MoveToPoint(0, self.rheight+self.sep*2)
        path.AddLineToPoint(self.rwidth, self.rheight+self.sep*2)
        path.AddLineToPoint(self.rwidth+self.thickness/2,
                            self.rheight+self.sep*2+self.thickness/2)
        path.AddLineToPoint(self.rwidth, self.rheight+self.sep*2+self.thickness)
        path.AddLineToPoint(0, self.rheight+self.sep*2+self.thickness)
        path.AddLineToPoint(0-self.thickness/2,
                            self.rheight+self.sep*2+self.thickness/2)
        path.CloseSubpath()
        return path


    def GetPathDot(self, gc):
        path = gc.CreatePath()
        if self.enable_dot:
            path.MoveToPoint(self.rwidth+self.sep+self.thickness*2,
                             self.rheight*2+self.thickness*1.5+self.sep*4)

            x, y = path.GetCurrentPoint()

            # TODO should be calc'd...
            if not self.tilt:
                path.AddCircle(x, y, self.thickness/2)

            path.CloseSubpath()
        return path


    def GetPathColon(self, gc):
        path = gc.CreatePath()
        if self.enable_colon:
            path.MoveToPoint(self.rwidth+self.sep+self.thickness*2.5,
                            self.rheight-self.thickness*0.5+self.sep)
            x, y = path.GetCurrentPoint()

            # TODO should be calc'd...
            if 1:#self.tilt:
                path.AddCircle(x, y, self.thickness/3)

            path.CloseSubpath()
        return path


    def SetValue(self, value):
        # Values will be converted to uppercase strings.
        # An invalid value will be silent ignored and converted to
        # an empty space.

        # Examples of valid values:
        #   3 or "3" - will display a '3'

        #   "A"     - all decimal and hex digits ar allowed, but also some other
        #             ones as per the _opts dict.

        #   "3."    - will display a '3' with a trailing dot (if EnableDot
        #             is True, which it is, by default)

        #   "3:"    - will display a '3' with a trailing colon (if EnableColon
        #             is True, which it is, by default)

        #   "3.:" or "3:."
        #           - will display a trailing dot and a trailing colon (if
        #             EnableDot and EnableColon are True -- they are, by
        #             default)

        #   "." or " ."
        #           - will display an empty display with a trailing dot

        #   ":" or " :"
        #           - will display an empty display with a trailing colon

        #   ".:" or ":." or " .:" or " :."
        #           - will display an empty display with a trailing dot
        #             and a trailing colon

        self.value = str(value).upper()
        self.Refresh()


    def SetTilt(self, value):
        self.tilt = value
        self.InitBuffer()
        self.Refresh()


    def GetTilt(self):
        return self.tilt


    def SetColours(self, **kwargs):
        # keywords: 'background', 'segment_on', 'segment_off'
        # values: wx.Colour or (colour) valid 3 or 4-tuple.
        # e.g: SetColours(segment_on=(255, 0, 0), background=wx.BLACK)

        if "background" in kwargs.keys():
            self.colours.background = kwargs["background"]

        if "segment_on" in kwargs.keys():
            self.colours.pen_seg_on = kwargs["segment_on"]
            self.colours.brush_seg_on = kwargs["segment_on"]

        if "segment_off" in kwargs.keys():
            self.colours.pen_seg_off = kwargs["segment_off"]
            self.colours.brush_seg_off = kwargs["segment_off"]

        self.Refresh()


    def GetColours(self):
        return {"background":  self.colours.background,
                "segment_on":  self.colours.pen_seg_on,
                "segment_off": self.colours.pen_seg_off}


    def SetGeometry(self, **kwargs):
        # keywords: thickness, width, height, separation
        # values: int
        # e.g: SetGeometry(thickness=28, separation=1)

        if "thickness" in kwargs.keys():
            self.thickness = kwargs["thickness"]
            self.radius = self.thickness

        if "width" in kwargs.keys():
            self.rwidth = kwargs["width"]

        if "height" in kwargs.keys():
            self.rheight = kwargs["height"]

        if "separation" in kwargs.keys():
            self.sep = kwargs["separation"]

        self.InitBuffer()
        self.Refresh()


    def GetGeometry(self):
        return {"thickness":  self.thickness,
                "width":      self.rwidth,
                "height":     self.rheight,
                "separation": self.sep}


    def EnableDot(self, val):
        # val: bool
        self.enable_dot = val
        self.InitBuffer()
        self.Refresh()


    def IsDotEnabled(self):
        return self.enable_dot


    def EnableColon(self, val):
        # val: bool
        self.enable_colon = val
        self.InitBuffer()
        self.Refresh()


    def IsColonEnabled(self):
        return self.enable_colon


# test stuff -------------------------------------------------------------------

class myFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, title="led test")

        self.SetSize((400, 400))

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.disps = []
        for i in range(0, 6):
            t = SevenSegmentDisp(self)
            sizer.Add(t, 1, flag=wx.EXPAND)
            self.disps.append(t)

        self.SetSizer(sizer)

        self.CentreOnScreen()

        self.tc = 1
        self.timer = wx.Timer(self)
        self.timer.Start(500)

        self.Bind(wx.EVT_TIMER, self.OnTimer)


    def OnTimer(self, evt):
        self.tc = -self.tc
        t = time.localtime(time.time())
        st = time.strftime("%H%M%S", t)

        vals = [i for i in st]
        if self.tc > 0:
            vals[1] += ":"
            vals[3] += ":"

        for i in range(0, 6):
            self.disps[i].SetValue(vals[i])

#-------------------------------------------------------------------------------

class myApp(wx.App):
    def OnInit(self):
        frame = myFrame(None)
        frame.Show(True)
        return True

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    import time
    app = myApp(0)
    app.MainLoop()


#
##
### eof
