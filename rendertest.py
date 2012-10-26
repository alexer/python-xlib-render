import Xlib.display
from Xlib import X

def match_visual_info(screen, depth, visual_class):
	for depth_info in screen.allowed_depths:
		if depth_info.depth != depth:
			continue
		for visual_info in depth_info.visuals:
			if visual_info.visual_class != visual_class:
				continue
			return visual_info.visual_id

dpy = Xlib.display.Display()
scr = dpy.screen()
root = scr.root

assert dpy.has_extension('RENDER')

res = dpy.render_query_version(0, 11)
print res.major_version, res.minor_version

res = dpy.render_query_pict_formats()

print 'Depths:', res.depths
print 'Visuals:', res.visuals
print 'Formats:'
for item in res.formats:
	print '-', item
print 'Screens:'
for item in res.screens:
	print '- Screen:'
	print '  - Fallback:', item.fallback
	print '  - Depths:'
	for depth in item.depths:
		print '    - Depth', depth.depth
		for visual in depth.visuals:
			print '      -', visual
print 'Subpixels:'
for item in res.subpixels:
	print '-', item

#dpy.render_query_pict_index_values(?)

depth = 32
visual = match_visual_info(scr, depth, X.TrueColor)
colormap = root.create_colormap(visual, X.AllocNone)
win = root.create_window(0, 0, 100, 100, 0, depth, X.CopyFromParent, visual, colormap = colormap, background_pixel = 0xffffffff, border_pixel = 0, event_mask = X.ExposureMask)
win.map()

while 1:
	ev = dpy.next_event()
	if ev.type == X.Expose:
		gc = ev.window.create_gc(foreground = 0xffff0000, background = 0xffff0000)
		ev.window.fill_rectangle(gc, 20, 20, 60, 60)

		pict = ev.window.render_create_picture(118)
		dpy.render_composite(1, pict, X.NONE, pict, 0, 0, 0, 0, 40, 40, 40, 40)

		pixmap = ev.window.create_pixmap(16, 16, 32)
		pixmap.put_image(gc, 0, 0, 16, 16, X.ZPixmap, 32, 0, '\x00\xff\x00\xff'*16*16)
		pict = pixmap.render_create_picture(118)
		pixmap.free()

		cursor = dpy.render_create_cursor(pict, 0, 0)
		ev.window.change_attributes(cursor = cursor)

		gc.free()

