# This file is part of MyPaint.
# Copyright (C) 2007 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY. See the COPYING file for more details.

"select color window (GTK and an own window)"
import gtk, gobject
import colorsys
from lib import helpers, mypaintlib
gdk = gtk.gdk

# GTK selector
class Window(gtk.Window):
    def __init__(self, app):
        gtk.Window.__init__(self)
        self.app = app
        self.add_accel_group(self.app.accel_group)

        self.set_title('Color')
        self.connect('delete-event', self.app.hide_window_cb)

        vbox = gtk.VBox()
        self.add(vbox)

        self.cs = gtk.ColorSelection()
        self.cs.connect('color-changed', self.color_changed_cb)
        vbox.pack_start(self.cs)

        self.alternative = None

    def show_change_color_window(self):
        if self.alternative:
            # second press: <strike>pick color</strike> cancel and remove the window
            #self.pick_color_at_pointer()
            self.alternative.remove_cleanly()
        else:
            self.alternative = AlternativeColorSelectorWindow(self)

    def color_changed_cb(self, cs):
        self.app.brush.set_color_hsv(self.get_color_hsv())

    def update(self):
        self.set_color_hsv(self.app.brush.get_color_hsv())

    def get_color_hsv(self):
        c = self.cs.get_current_color()
        r = float(c.red  ) / 65535
        g = float(c.green) / 65535
        b = float(c.blue ) / 65535
        assert r >= 0.0
        assert g >= 0.0
        assert b >= 0.0
        assert r <= 1.0
        assert g <= 1.0
        assert b <= 1.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return (h, s, v)

    def set_color_hsv(self, hsv):
        h, s, v = hsv
        while h > 1.0: h -= 1.0
        while h < 0.0: h += 1.0
        if s > 1.0: s = 1.0
        if s < 0.0: s = 0.0
        if v > 1.0: v = 1.0
        if v < 0.0: v = 0.0
        r, g, b  = colorsys.hsv_to_rgb(h, s, v)
        c = gdk.Color(int(r*65535+0.5), int(g*65535+0.5), int(b*65535+0.5))
        self.cs.set_current_color(c)


# own color selector
# see also get_colorselection_pixbuf in colorselector.hpp
class AlternativeColorSelectorWindow(gtk.Window):
    def __init__(self, colorselectionwindow):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_gravity(gdk.GRAVITY_CENTER)
        self.set_position(gtk.WIN_POS_MOUSE)
        
        self.colorselectionwindow = colorselectionwindow
        self.app = colorselectionwindow.app
        self.add_accel_group(self.app.accel_group)

        #self.set_title('Color')
        self.connect('delete-event', self.app.hide_window_cb)

        self.image = image = gtk.Image()
        self.add(image)
        
        self.h, self.s, self.v = self.app.brush.get_color_hsv()
        self.update_image()

	self.set_events(gdk.BUTTON_PRESS_MASK |
                        gdk.BUTTON_RELEASE_MASK |
                        gdk.ENTER_NOTIFY |
                        gdk.LEAVE_NOTIFY
                        )
        self.connect("enter-notify-event", self.enter_notify_cb)
        self.connect("leave-notify-event", self.leave_notify_cb)
        self.connect("button-release-event", self.button_release_cb)
        self.connect("button-press-event", self.button_press_cb)

        self.destroy_timer = None
        self.button_pressed = False

        self.show_all()

        self.window.set_cursor(gdk.Cursor(gdk.CROSSHAIR))
    
    def update_image(self):
        size = mypaintlib.colorselector_size
        pixbuf = gdk.Pixbuf(gdk.COLORSPACE_RGB, True, 8, size, size)
        arr = pixbuf.get_pixels_array()
        arr = mypaintlib.gdkpixbuf2numpy(arr)
        mypaintlib.render_swisscheesewheelcolorselector(arr, self.h, self.s, self.v)
        pixmap, mask = pixbuf.render_pixmap_and_mask()
        self.image.set_from_pixmap(pixmap, mask)
        self.shape_combine_mask(mask,0,0)
        
    def pick_color(self,x,y):
        self.h, self.s, self.v = mypaintlib.pick_scwcs_hsv_at( x, y, self.h, self.s, self.v )
        self.colorselectionwindow.set_color_hsv((self.h, self.s, self.v))
    
    def button_press_cb(self, widget, event):
        if event.button == 1:
          self.pick_color(event.x,event.y)
        self.button_pressed = True

    def remove_cleanly(self):
        self.colorselectionwindow.alternative = None
        if self.destroy_timer is not None:
            gobject.source_remove(self.destroy_timer)
            self.destroy_timer = None
        self.destroy()

    def button_release_cb(self, widget, event):
        if self.button_pressed:
            if event.button == 1:
                self.pick_color(event.x,event.y)
                self.update_image()

    def enter_notify_cb(self, widget, event):
        if self.destroy_timer is not None:
            gobject.source_remove(self.destroy_timer)
            self.destroy_timer = None

    def leave_notify_cb(self, widget, event):
        # allow to leave the window for a short time
        if self.destroy_timer is not None:
            gobject.source_remove(self.destroy_timer)
        self.destroy_timer = gobject.timeout_add(200, self.remove_cleanly)
