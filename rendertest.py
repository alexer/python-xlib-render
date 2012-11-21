import Xlib.display
from Xlib import X
import xutil
import struct

def generate_glyphs(glyphids):
	import Image
	import ImageFont
	import ImageDraw

	font = ImageFont.load_default()
	w, h = size = font.getsize(' ')
	# Each image row needs to be padded
	im = Image.new('RGB', (w + (4 - w) % 4, h))
	draw = ImageDraw.Draw(im)

	glyphs = []
	for i in glyphids:
		draw.rectangle(((0, 0), size), fill=(0, 0, 0))
		draw.text((0, 0), chr(i), font=font)
		glyphs.append((i, (w, h, 0, 0, w, 0), ''.join(map(chr, im.convert('L').getdata()))))

	return glyphs

def generate_cursor(win):
	width = height = 16
	depth = 32
	cursors = []
	gc = win.create_gc()
	for i in range(0, 1530, 15):
		color = [min(max((abs(765 - ((i + c * 510) % 1530)) - 255), 0), 255) for c in range(3)]
		color = struct.pack('<3B', *color)
		pixels = ''.join(color + ('\x7f' if x == y else '\xff') if x >= y else '\x00\x00\x00\x00' for y in range(height) for x in range(width))
		pixmap = win.create_pixmap(width, height, depth)
		pixmap.put_image(gc, 0, 0, width, height, X.ZPixmap, depth, 0, pixels)
		pict = pixmap.create_picture(fmt_argb32)
		pixmap.free()
		# OP 27, CreateCursor
		cursor = pict.create_cursor(0, 0)
		cursors.append((cursor, 100))
		pict.free()
	gc.free()
	# OP 31, CreateAnimCursor
	cursor = dpy.create_anim_cursor(cursors)

	return cursor

# XXX: Untested
# XXX: OP 2, QueryPictIndexValues
# XXX: OP 9, Scale

dpy = Xlib.display.Display()
scr = dpy.screen()
root = scr.root

assert dpy.has_extension('RENDER')

# OP 0, QueryVersion
res = dpy.render_query_version()
print 'XRender version:', res.major_version, res.minor_version

# OP 1, QueryPictFormats
res = dpy.render_query_pict_formats()

depths = visuals = 0
print 'Formats:'
for item in res.formats:
	print '-', item
print 'Screens:'
for screen in res.screens:
	print '- Screen:'
	print '  - Fallback:', screen.fallback
	print '  - Depths:'
	for depth in screen.depths:
		print '    - Depth', depth.depth
		for visual in depth.visuals:
			print '      -', visual
		visuals += len(depth.visuals)
	depths += len(screen.depths)
print 'Subpixels:'
for item in res.subpixels:
	print '-', item

assert depths == res.depths
assert visuals == res.visuals

fmt_argb32 = xutil.render_find_standard_format(dpy, xutil.PictStandardARGB32)['id']
fmt_a8 = xutil.render_find_standard_format(dpy, xutil.PictStandardA8)['id']

depth = 32
visual = xutil.match_visual_info(scr, depth, X.TrueColor)
colormap = root.create_colormap(visual, X.AllocNone)
win = root.create_window(0, 0, 200, 200, 0, depth, X.CopyFromParent, visual, colormap = colormap, background_pixel = 0xffffffff, border_pixel = 0, event_mask = X.ExposureMask)
win.map()

WM_DELETE_WINDOW = dpy.intern_atom('WM_DELETE_WINDOW')
WM_PROTOCOLS = dpy.intern_atom('WM_PROTOCOLS')

win.set_wm_protocols([WM_DELETE_WINDOW])

glyphids = range(32, 127)
glyphs = generate_glyphs(glyphids)

# OP 17, CreateGlyphSet
font_ = dpy.create_glyph_set(fmt_a8)
# OP 20, AddGlyphs
font_.add_glyphs(*glyphs)
# OP 18, ReferenceGlyphSet
font = font_.reference()
font_.free()

cursor = generate_cursor(win)
win.change_attributes(cursor = cursor)

# OP 4, CreatePicture
pict = win.create_picture(fmt_argb32)

red = (65535, 0, 0, 65535)
green = (0, 65535, 0, 65535)
blue = (0, 0, 65535, 65535)
stops = [(0, red), (0.5, green), (1, blue)]

gradients = [
	# OP 33, CreateSolidFill
	dpy.create_solid_fill(green),
	# OP 34, CreateLinearGradient
	dpy.create_linear_gradient((0, 0), (50, 50), *stops),
	# OP 35, CreateRadialGradient
	dpy.create_radial_gradient((40, 5), (40, 5), 0, 40, *stops),
	# OP 36, CreateConicalGradient
	dpy.create_conical_gradient((40, 5), 180, *stops),
]
hue = dpy.create_conical_gradient((50, 50), 0, (0/6., (65535, 0, 0, 65535)), (1/6., (65535, 0, 65535, 65535)), (2/6., (0, 0, 65535, 65535)), (3/6., (0, 65535, 65535, 65535)), (4/6., (0, 65535, 0, 65535)), (5/6., (65535, 65535, 0, 65535)), (6/6., (65535, 0, 0, 65535)))

pixmap = win.create_pixmap(100, 100, 32)
img = pixmap.create_picture(fmt_argb32)
# OP 29, QueryFilters
res = pixmap.render_query_filters()
pixmap.free()

pixmap = win.create_pixmap(100, 100, 32)
img2 = pixmap.create_picture(fmt_argb32)
pixmap.free()

pixmap = win.create_pixmap(100, 100, 8)
mask = pixmap.create_picture(fmt_a8)
pixmap.free()

mask.fill_rectangles(0, (0, 0, 0, 0), (0, 0, 100, 100))
# OP 32, AddTraps
mask.add_traps(10, 10, ((10, 30, 0), (0, 40, 20)), ((0, 40, 20), (10, 30, 40)))
if 'convolution' in res.filters:
	mask.set_filter('convolution', 7, 7, *[1./(7*7) for i in range(49)])

img.fill_rectangles(0, (0, 0, 0, 0), (0, 0, 100, 100))
# OP 6, SetPictureClipRectangles
img.set_clip_rectangles(0, 0, (0, 0, 60, 25), (0, 0, 25, 60), (0, 35, 60, 25), (35, 0, 25, 60))
# OP 8, Composite
img.composite(3, hue, mask, 20, 20, 0, 0, 0, 0, 60, 60)

img2.fill_rectangles(0, (0, 0, 0, 0), (0, 0, 100, 100))
img2.set_clip_rectangles(0, 0, (0, 0, 60, 25), (0, 0, 25, 60), (0, 35, 60, 25), (35, 0, 25, 60))
# OP 5, ChangePicture
img2.change(clip_mask = X.NONE)
img2.composite(3, hue, mask, 20, 20, 0, 0, 0, 0, 60, 60)

# OP 28, SetPictureTransform
mask.set_transform((1, 0.2, 0, 0, 1, 0, 0, 0, 1))
# OP 30, SetPictureFilter
mask.set_filter('good')

while 1:
	ev = dpy.next_event()
	if ev.type == X.Expose:
		funcs = [pict.composite_glyphs_8, pict.composite_glyphs_16, pict.composite_glyphs_32, pict.composite_glyphs]
		for i, (gradient, func) in enumerate(zip(gradients, funcs)):
			# OP 23, CompositeGlyphs8
			# OP 24, CompositeGlyphs16
			# OP 25, CompositeGlyphs32
			func(3, gradient, X.NONE, font, 0, 0, (20, 15 + 20 * i, map(ord, 'Hello, world!')), font, (-50, 10, map(ord, '---')))
		# OP 26, FillRectangles
		pict.fill_rectangles(3, (65535, 32767, 0, 65535), (120, 10, 20, 20), (120, 40, 20, 20))
		# OP 10, Trapezoids
		pict.trapezoids(3, gradients[0], fmt_a8, 0, 0, (70, 90, ((120, 70), (110, 90)), ((140, 70), (150, 90))))
		# OP 11, Triangles
		pict.triangles(3, gradients[0], X.NONE, 0, 0, ((160, 10), (150, 30), (180, 15)), ((160, 30), (190, 15), (180, 30)))
		# OP 12, TriStrip
		pict.tri_strip(3, gradients[0], X.NONE, 0, 0, (150, 70), (160, 90), (170, 75), (180, 85))
		# OP 13, TriFan
		pict.tri_fan(3, gradients[0], X.NONE, 0, 0, (160, 50), (150, 40), (155, 60), (165, 60), (170, 40))
		pict.composite(3, gradients[0], X.NONE, 0, 0, 0, 0, 180, 40, 10, 20)
		pict.composite(3, hue, mask, 20, 20, 0, 0, 10, 100, 100, 100)
		pict.composite(3, img, X.NONE, 0, 0, 0, 0, 60, 100, 100, 100)
		pict.composite(3, img2, X.NONE, 0, 0, 0, 0, 120, 100, 100, 100)
	elif ev.type == X.ClientMessage:
		if ev.client_type == WM_PROTOCOLS:
			fmt, data = ev.data
			if fmt == 32 and data[0] == WM_DELETE_WINDOW:
				break

# OP 22, FreeGlyphs
font.free_glyphs(*glyphids)
# OP 19, FreeGlyphSet
font.free()
# OP 7, FreePicture
pict.free()

