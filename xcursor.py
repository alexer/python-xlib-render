import struct
from Xlib import X

def chunk(data, size):
	assert size <= len(data)
	return data[:size], data[size:]

def unpack(data, size, fmt):
	this, rest = chunk(data, size)
	return struct.unpack(fmt, this), rest

def parse_cursor(data):
	magic, data = chunk(data, 4)
	assert magic == 'Xcur'

	(header_size, version, toc_count), data = unpack(data, 12, '<III')
	#print 'HDR: size, version, count =', (header_size, version, toc_count)
	assert header_size == 16

	tocs = []
	for i in range(toc_count):
		item, data = unpack(data, 12, '<III')
		type, subtype, position = item
		tocs.append(item)
		#print 'TOC: type, subtype, position =', item

	assert tocs[0][2] == header_size + toc_count * 12

	imgs = []
	pos = header_size + toc_count * 12
	for toc_type, toc_subtype, toc_position in tocs:
		assert toc_position == pos

		item, data = unpack(data, 16, '<IIII')
		header_size, type, subtype, version = item
		#print 'CHUNK: size, type, subtype, version =', item

		assert header_size == {0xfffe0001: 20, 0xfffd0002: 36}[type]
		assert toc_type == type
		assert toc_subtype == subtype

		if type == 0xfffe0001:
			assert subtype in (1, 2, 3)
			assert version == 1
			item, data = unpack(data, 4, '<I')
			length, = item
			string, data = chunk(data, length)
			#print 'STR:', repr(string)
		if type == 0xfffd0002:
			assert version == 1
			item, data = unpack(data, 20, '<IIIII')
			width, height, xhot, yhot, delay = item
			#print 'IMG: width, height, xhot, yhot, delay =', item
			assert width <= 0x7fff
			assert height <= 0x7fff
			assert xhot <= width
			assert yhot <= height
			length = width * height * 4
			pixels, data = chunk(data, length)
			imgs.append((width, height, xhot, yhot, delay, pixels))

		pos += header_size + length

	assert len(data) == 0

	return imgs

def create_cursor(win, format_id, width, height, xhot, yhot, pixels):
	gc = win.create_gc()
	pixmap = win.create_pixmap(width, height, 32)
	pixmap.put_image(gc, 0, 0, width, height, X.ZPixmap, 32, 0, pixels)
	gc.free()
	pict = pixmap.create_picture(format_id)
	pixmap.free()
	cursor = pict.create_cursor(xhot, yhot)
	pict.free()
	return cursor

def load_cursor(dpy, win, format_id, fname):
	data = file(fname, 'rb').read()
	cursors = []
	for (width, height, xhot, yhot, delay, pixels) in parse_cursor(data):
		cursor = create_cursor(win, format_id, width, height, xhot, yhot, pixels)
		cursors.append((cursor, delay))
	if len(cursors) <= 1:
		return cursors[0][0]
	return dpy.create_anim_cursor(cursors)

if __name__ == '__main__':
	data = file('/usr/share/icons/Oxygen_Black/cursors/wait', 'rb').read()
	parse_cursor(data)

