import Xlib.display
from Xlib import X
import xcursor

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

def render_find_format(**kwargs):
	matches = []
	for item in res.formats:
		for key, value in kwargs.iteritems():
			if item[key] != value:
				break
		else:
			matches.append(item)
	return matches

format_id = render_find_format(depth=32, alpha_shift=24, red_shift=16, green_shift=8, blue_shift=0, alpha_mask=255, red_mask=255, green_mask=255, blue_mask=255)[0]['id']
print format_id

#dpy.render_query_pict_index_values(?)

depth = 32
visual = match_visual_info(scr, depth, X.TrueColor)
colormap = root.create_colormap(visual, X.AllocNone)
win = root.create_window(0, 0, 100, 100, 0, depth, X.CopyFromParent, visual, colormap = colormap, background_pixel = 0xffffffff, border_pixel = 0, event_mask = X.ExposureMask)
win.map()

def create_cursor(win, width, height, xhot, yhot, pixels):
	gc = win.create_gc()
	pixmap = win.create_pixmap(width, height, 32)
	pixmap.put_image(gc, 0, 0, width, height, X.ZPixmap, 32, 0, pixels)
	gc.free()
	pict = pixmap.create_picture(format_id)
	pixmap.free()
	cursor = pict.create_cursor(xhot, yhot)
	pict.free()
	return cursor

def load_cursor(dpy, win, fname):
	data = file(fname, 'rb').read()
	cursors = []
	for (width, height, xhot, yhot, delay, pixels) in xcursor.parse_cursor(data):
		cursor = create_cursor(ev.window, width, height, xhot, yhot, pixels)
		cursors.append((cursor, delay))
	if len(cursors) <= 1:
		return cursors[0][0]
	return dpy.create_anim_cursor(cursors)

while 1:
	ev = dpy.next_event()
	if ev.type == X.Expose:
		gc = ev.window.create_gc(foreground = 0xffff0000, background = 0xffff0000)
		ev.window.fill_rectangle(gc, 20, 20, 60, 60)

		pict = ev.window.create_picture(format_id)
		dpy.render_composite(1, pict, X.NONE, pict, 0, 0, 0, 0, 40, 40, 40, 40)
		pict.free()

		cursor = load_cursor(dpy, ev.window, '/usr/share/icons/Oxygen_Black/cursors/half-busy')
		ev.window.change_attributes(cursor = cursor)

		gc.free()

