
# Utility functions defined in Xlib but not python-xlib

def match_visual_info(screen, depth, visual_class):
	for depth_info in screen.allowed_depths:
		if depth_info.depth != depth:
			continue
		for visual_info in depth_info.visuals:
			if visual_info.visual_class != visual_class:
				continue
			return visual_info.visual_id

# XRender* utility functions

PictStandardARGB32 = 0
PictStandardRGB24 = 1
PictStandardA8 = 2
PictStandardA4 = 3
PictStandardA1 = 4

PictTypeIndexed = 0
PictTypeDirect = 1

def render_find_format(dpy, **kwargs):
	res = dpy.render_query_pict_formats()
	matches = []
	for item in res.formats:
		for key, value in kwargs.iteritems():
			if item[key] != value:
				break
		else:
			matches.append(item)
	return matches

def render_find_standard_format(dpy, fmt):
	standard_formats = [
		dict(type=PictTypeDirect, depth=32, alpha_shift=24, red_shift=16, green_shift=8, blue_shift=0, alpha_mask=255, red_mask=255, green_mask=255, blue_mask=255),
		dict(type=PictTypeDirect, depth=24,                 red_shift=16, green_shift=8, blue_shift=0, alpha_mask=0,   red_mask=255, green_mask=255, blue_mask=255),
		dict(type=PictTypeDirect, depth=8,  alpha_shift=0,                                             alpha_mask=255, red_mask=0,   green_mask=0,   blue_mask=0),
		dict(type=PictTypeDirect, depth=4,  alpha_shift=0,                                             alpha_mask=15,  red_mask=0,   green_mask=0,   blue_mask=0),
		dict(type=PictTypeDirect, depth=1,  alpha_shift=0,                                             alpha_mask=1,   red_mask=0,   green_mask=0,   blue_mask=0),
	]
	return render_find_format(dpy, **standard_formats[fmt])[0]

