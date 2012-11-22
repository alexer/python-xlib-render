#
# Xlib.ext.render -- Rendering extension module
#
#    Copyright (C) 2011-2012 Aleksi Torhamo <aleksi@torhamo.net>
#
"""Rendering extension"""

import struct
import types

from Xlib import X
from Xlib.protocol import rq, structs
from Xlib.xobject import drawable, resource, cursor

extname = 'RENDER'

class Fixed(rq.Card32):
    def check_value(self, value):
        return int(value*2**16)

    def parse_value(self, value, display):
        return value/float(2**16)

FixedObj = Fixed(None)

Indexed = 0
Direct = 1

VisualId = rq.Card32
PictFormat = rq.Card32
Atom = rq.Card32
Subpixel = rq.Struct(
    rq.Set('subpixel', 1, (0, 1, 2, 3, 4, 5)),
    rq.Card8('xxx'),
    rq.Pad(2),
    )
DirectFormat = rq.Struct(
    rq.Card16('red_shift'),
    rq.Card16('red_mask'),
    rq.Card16('green_shift'),
    rq.Card16('green_mask'),
    rq.Card16('blue_shift'),
    rq.Card16('blue_mask'),
    rq.Card16('alpha_shift'),
    rq.Card16('alpha_mask'),
    )
PictFormInfo = rq.Struct(
    PictFormat('id'),
    rq.Set('type', 1, (Indexed, Direct)),
    rq.Card8('depth'),
    rq.Pad(2),
    #DirectFormat,
    rq.Card16('red_shift'),
    rq.Card16('red_mask'),
    rq.Card16('green_shift'),
    rq.Card16('green_mask'),
    rq.Card16('blue_shift'),
    rq.Card16('blue_mask'),
    rq.Card16('alpha_shift'),
    rq.Card16('alpha_mask'),

    rq.Colormap('colormap', (X.NONE, )),
    )
PictVisual = rq.Struct(
    VisualId('visual', (X.NONE, )),
    PictFormat('format'),
    )
PictDepth = rq.Struct(
    rq.Card8('depth'),
    rq.Pad(1),
    rq.LengthOf('visuals', 2),
    rq.Pad(4),
    rq.List('visuals', PictVisual)
    )
PictScreen = rq.Struct(
    rq.LengthOf('depths', 4),
    PictFormat('fallback'),
    rq.List('depths', PictDepth),
    )
IndexValue = rq.Struct(
    rq.Card32('pixel'),
    rq.Card16('red'),
    rq.Card16('green'),
    rq.Card16('blue'),
    rq.Card16('alpha'),
    )
AnimCursorElt = rq.Struct(
    rq.Cursor('cursor'),
    rq.Card32('delay'),
    )
Transform = rq.Struct(
    Fixed('p11'),
    Fixed('p12'),
    Fixed('p13'),
    Fixed('p21'),
    Fixed('p22'),
    Fixed('p23'),
    Fixed('p31'),
    Fixed('p32'),
    Fixed('p33'),
    )
Color = rq.Struct(
    rq.Card16('red'),
    rq.Card16('green'),
    rq.Card16('blue'),
    rq.Card16('alpha'),
    )
PointFix = rq.Struct(
    Fixed('x'),
    Fixed('y'),
    )
LineFix = rq.Struct(
    rq.Object('p1', PointFix),
    rq.Object('p2', PointFix),
    )
Trapezoid = rq.Struct(
    Fixed('top'),
    Fixed('bottom'),
    rq.Object('left', LineFix),
    rq.Object('right', LineFix),
    )
Triangle = rq.Struct(
    rq.Object('p1', PointFix),
    rq.Object('p2', PointFix),
    rq.Object('p3', PointFix),
    )
GlyphInfo = rq.Struct(
    rq.Card16('width'),
    rq.Card16('height'),
    rq.Int16('x'),
    rq.Int16('y'),
    rq.Int16('off_x'),
    rq.Int16('off_y'),
    )
GlyphElt8 = rq.Struct(
    rq.LengthOf('glyphs', 1),
    rq.Pad(3),
    rq.Int16('deltax'),
    rq.Int16('deltay'),
    rq.List('glyphs', rq.Card8),
    )
GlyphElt16 = rq.Struct(
    rq.LengthOf('glyphs', 1),
    rq.Pad(3),
    rq.Int16('deltax'),
    rq.Int16('deltay'),
    rq.List('glyphs', rq.Card16),
    )
GlyphElt32 = rq.Struct(
    rq.LengthOf('glyphs', 1),
    rq.Pad(3),
    rq.Int16('deltax'),
    rq.Int16('deltay'),
    rq.List('glyphs', rq.Card32),
    )
# XXX: List or StringN?
SpanFix = rq.Struct(
    Fixed('left'),
    Fixed('right'),
    Fixed('y'),
    )
Trap = rq.Struct(
    rq.Object('top', SpanFix),
    rq.Object('bottom', SpanFix),
    )

class GlyphItems(rq.ValueField):
    glyphelt = None
    def pack_value(self, value):
        data = ''
        args = {}

        for v in value:
            # Let values be simple strings, meaning a delta of 0
            if type(v) is types.StringType:
                v = (0, 0, v)

            # A tuple, it should be (deltax, deltay, string)
            # Encode it as one or more textitems

            if type(v) in (types.TupleType, types.DictType) or \
               isinstance(v, rq.DictWrapper):

                if type(v) is types.TupleType:
                    deltax, deltay, str = v
                else:
                    deltax = v['deltax']
                    deltay = v['deltay']
                    str = v['glyphs']

                while deltax or deltay or str:
                    args['deltax'] = deltax
                    args['deltay'] = deltay
                    args['glyphs'] = str[:254]

                    data = data + apply(self.glyphelt.to_binary, (), args)

                    deltax = deltay = 0
                    str = str[254:]

            # Else an integer, i.e. a font change
            else:
                # Use fontable cast function if instance
                if type(v) is types.InstanceType:
                    v = v.__glyphset__()

                # XXX: Endianness?
                data = data + struct.pack('<B3xHHL', 255, 0, 0, v)

        # Pad out to four byte length
        dlen = len(data)
        return data + '\0' * ((4 - dlen % 4) % 4), None, None

    def parse_binary_value(self, data, display, length, format):
        values = []
        while 1:
            if len(data) < 2:
                break

            # font change
            if ord(data[0]) == 255:
                # XXX: Make it a GlyphSet? Endianness?
                values.append(struct.unpack('<L', str(data[8:12]))[0])
                data = buffer(data, 12)

            # string with delta
            else:
                v, data = self.glyphelt.parse_binary(data, display)
                values.append(v)

        return values, ''


class GlyphItems8(GlyphItems):
    glyphelt = GlyphElt8


class GlyphItems16(GlyphItems):
    glyphelt = GlyphElt16


class GlyphItems32(GlyphItems):
    glyphelt = GlyphElt32


def PictOp(arg):
    return rq.Set(arg, 1, tuple(range(0x00, 0x0d+1) + range(0x10, 0x1b+1) + range(0x20, 0x2b+1) + range(0x30, 0x3e+1)))

def PictureValues(arg):
    return rq.ValueList(arg, 2, 2,
        rq.Set('repeat', 1, (0, 1, 2, 3)),
        rq.Picture('alpha_map'),
        rq.Int16('alpha_x_origin'),
        rq.Int16('alpha_y_origin'),
        rq.Int16('clip_x_origin'),
        rq.Int16('clip_y_origin'),
        rq.Pixmap('clip_mask'),
        rq.Bool('graphics_exposures'),
        rq.Set('subwindow_mode', 1, (0, 1)),
        rq.Set('poly_edge', 1, (0, 1)),
        rq.Set('poly_mode', 1, (0, 1)),
        Atom('dither'),
        rq.Bool('component_alpha'),
        )


class QueryVersion(rq.ReplyRequest):
    _request = rq.Struct(
            rq.Card8('opcode'),
            rq.Opcode(0),
            rq.RequestLength(),
            rq.Card32('major_version'),
            rq.Card32('minor_version')
            )

    _reply = rq.Struct(
            rq.ReplyCode(),
            rq.Pad(1),
            rq.Card16('sequence_number'),
            rq.ReplyLength(),
            rq.Card32('major_version'),
            rq.Card32('minor_version'),
            rq.Pad(16),
            )

def query_version(self):
    return QueryVersion(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        major_version = 0,
        minor_version = 11,
        )


class QueryPictFormats(rq.ReplyRequest):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(1),
        rq.RequestLength(),
        )

    _reply = rq.Struct(
        rq.ReplyCode(),
        rq.Pad(1),
        rq.Card16('sequence_number'),
        rq.ReplyLength(),
        rq.LengthOf('formats', 4),
        rq.LengthOf('screens', 4),
        rq.Card32('depths', 4),
        rq.Card32('visuals', 4),
        rq.LengthOf('subpixels', 4),
        rq.Pad(4),
        rq.List('formats', PictFormInfo),
        rq.List('screens', PictScreen),
        rq.List('subpixels', Subpixel),
        )

def query_pict_formats(self):
    """Query PictFormats supported by the server.
    """
    return QueryPictFormats(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        )


# XXX: Untested, my X sever returned BadMatch on every format I tried; no indexed PictFormats?
class QueryPictIndexValues(rq.ReplyRequest):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(2),
        rq.RequestLength(),
        PictFormat('format'),
        )

    _reply = rq.Struct(
        rq.ReplyCode(),
        rq.Pad(1),
        rq.Card16('sequence_number'),
        rq.ReplyLength(),
        rq.LengthOf('indexvalues', 4),
        rq.Pad(20),
        rq.List('indexvalues', IndexValue),
        )

def query_pict_index_values(self, format):
    return QueryPictIndexValues(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        format = format,
        )


# XXX: Not implemented (not in spec)
# QueryDithers, opcode=3


class CreatePicture(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(4),
        rq.RequestLength(),
        rq.Picture('pid'),
        rq.Drawable('drawable'),
        PictFormat('format'),
        PictureValues('values'),
        )

def create_picture(self, format, **keys):
    pid = self.display.allocate_resource_id()
    CreatePicture(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        pid = pid,
        drawable = self,
        format = format,
        values = keys,
        )
    cls = self.display.get_resource_class('picture', Picture)
    return cls(self.display, pid, owner = 1)


class ChangePicture(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(5),
        rq.RequestLength(),
        rq.Picture('picture'),
        PictureValues('values'),
        )


class SetPictureClipRectangles(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(6),
        rq.RequestLength(),
        rq.Picture('picture'),
        rq.Int16('clip_x_origin'),
        rq.Int16('clip_y_origin'),
        rq.List('rectangles', structs.Rectangle),
        )


class FreePicture(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(7),
        rq.RequestLength(),
        rq.Picture('picture'),
        )


class Composite(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(8),
        rq.RequestLength(),
        rq.Card8('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('mask'),
        rq.Picture('dst'),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.Int16('mask_x'),
        rq.Int16('mask_y'),
        rq.Int16('dst_x'),
        rq.Int16('dst_y'),
        rq.Card16('width'),
        rq.Card16('height'),
        )


# XXX: Untested (not in spec)
class Scale(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(9),
        rq.RequestLength(),
        rq.Picture('src'),
        rq.Picture('dst'),
        rq.Card32('color_scale'),
        rq.Card32('alpha_scale'),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.Int16('dst_x'),
        rq.Int16('dst_y'),
        rq.Card16('width'),
        rq.Card16('height'),
        )


# The Trapezoids request is deprecated
class Trapezoids(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(10),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.List('traps', Trapezoid),
        )


class Triangles(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(11),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.List('triangles', Triangle),
        )


class TriStrip(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(12),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.List('points', PointFix),
        )


class TriFan(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(13),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        rq.List('points', PointFix),
        )


# XXX: Not implemented (not in spec)
# ColorTrapezoids, opcode=14
# ColorTriangles, opcode=15
## Transform, opcode=16


class CreateGlyphSet(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(17),
        rq.RequestLength(),
        rq.GlyphSet('gsid'),
        PictFormat('format'),
        )

def create_glyph_set(self, format):
    gsid = self.display.allocate_resource_id()
    CreateGlyphSet(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        gsid = gsid,
        format = format,
        )
    cls = self.display.get_resource_class('glyphset', GlyphSet)
    return cls(self.display, gsid, owner = 1)


class ReferenceGlyphSet(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(18),
        rq.RequestLength(),
        rq.GlyphSet('gsid'),
        rq.GlyphSet('existing'),
        )


class FreeGlyphSet(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(19),
        rq.RequestLength(),
        rq.GlyphSet('glyphset'),
        )


class AddGlyphs(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(20),
        rq.RequestLength(),
        rq.GlyphSet('glyphset'),
        rq.LengthOf(('glyphids', 'glyphs'), 4),
        rq.List('glyphids', rq.Card32),
        rq.List('glyphs', GlyphInfo),
        rq.String8('images'),
        )


class FreeGlyphs(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(22),
        rq.RequestLength(),
        rq.GlyphSet('glyphset'),
        rq.List('glyphs', rq.Card32),
        )


# XXX: Not implemented (not in spec)
# AddGlyphsFromPicture, opcode=21


# The spec says that the glyphset argument of CompositeGlyphs* is
# of type Glyphable, which means it's either GlyphSet or Fontable.
# I tried GC and Font, but my X server just gave XError, so for now
# I am assuming the spec is wrong/outdated and just used GlyphSet.


class CompositeGlyphs8(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(23),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.GlyphSet('glyphset'),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        GlyphItems8('glyphcmds'),
        )


class CompositeGlyphs16(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(24),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.GlyphSet('glyphset'),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        GlyphItems16('glyphcmds'),
        )


class CompositeGlyphs32(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(25),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('src'),
        rq.Picture('dst'),
        PictFormat('mask_format', (X.NONE, )),
        rq.GlyphSet('glyphset'),
        rq.Int16('src_x'),
        rq.Int16('src_y'),
        GlyphItems32('glyphcmds'),
        )


class FillRectangles(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(26),
        rq.RequestLength(),
        PictOp('op'),
        rq.Pad(3),
        rq.Picture('dst'),
        rq.Object('color', Color),
        rq.List('rects', structs.Rectangle),
        )


class CreateCursor(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(27),
        rq.RequestLength(),
        rq.Cursor('cid'),
        rq.Picture('source'),
        rq.Card16('x'),
        rq.Card16('y'),
        )


class SetPictureTransform(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(28),
        rq.RequestLength(),
        rq.Picture('picture'),
        rq.Object('transform', Transform),
        )


class QueryFilters(rq.ReplyRequest):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(29),
        rq.RequestLength(),
        rq.Drawable('drawable'),
        )

    _reply = rq.Struct(
        rq.ReplyCode(),
        rq.Pad(1),
        rq.Card16('sequence_number'),
        rq.LengthOf('aliases', 4),
        rq.LengthOf('filters', 4),
        rq.Pad(4),
        rq.List('aliases', rq.Card16),
        rq.List('filters', rq.Str),
        )

def query_filters(self):
    return QueryFilters(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        drawable = self,
        )


class SetPictureFilter(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(30),
        rq.RequestLength(),
        rq.Picture('picture'),
        rq.LengthOf('filter', 2),
        rq.Pad(2),
        rq.String8('filter'),
        rq.List('values', FixedObj),
        )


class CreateAnimCursor(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(31),
        rq.RequestLength(),
        rq.Cursor('cid'),
        rq.List('cursors', AnimCursorElt),
        )

def create_anim_cursor(self, cursors):
    cid = self.display.allocate_resource_id()
    CreateAnimCursor(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        cid = cid,
        cursors = cursors,
        )
    cls = self.display.get_resource_class('cursor', cursor.Cursor)
    return cls(self.display, cid, owner = 1)


class AddTraps(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(32),
        rq.RequestLength(),
        rq.Picture('picture'),
        rq.Int16('off_x'),
        rq.Int16('off_y'),
        rq.List('trapezoids', Trap),
        )


class CreateSolidFill(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(33),
        rq.RequestLength(),
        rq.Picture('pid'),
        rq.Object('color', Color),
        )

def create_solid_fill(self, color):
    pid = self.display.allocate_resource_id()
    CreateSolidFill(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        pid = pid,
        color = color,
        )
    cls = self.display.get_resource_class('picture', Picture)
    return cls(self.display, pid, owner = 1)


class CreateLinearGradient(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(34),
        rq.RequestLength(),
        rq.Picture('pid'),
        rq.Object('p1', PointFix),
        rq.Object('p2', PointFix),
        rq.LengthOf(('stops', 'stop_colors'), 4),
        rq.List('stops', FixedObj),
        rq.List('stop_colors', Color),
        )

def create_linear_gradient(self, p1, p2, *stops):
    pid = self.display.allocate_resource_id()
    CreateLinearGradient(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        pid = pid,
        p1 = p1,
        p2 = p2,
        stops = [stop[0] for stop in stops],
        stop_colors = [stop[1] for stop in stops],
        )
    cls = self.display.get_resource_class('picture', Picture)
    return cls(self.display, pid, owner = 1)


class CreateRadialGradient(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(35),
        rq.RequestLength(),
        rq.Picture('pid'),
        rq.Object('inner_center', PointFix),
        rq.Object('outer_center', PointFix),
        Fixed('inner_radius'),
        Fixed('outer_radius'),
        rq.LengthOf(('stops', 'stop_colors'), 4),
        rq.List('stops', FixedObj),
        rq.List('stop_colors', Color),
        )

def create_radial_gradient(self, inner_center, outer_center, inner_radius, outer_radius, *stops):
    pid = self.display.allocate_resource_id()
    CreateRadialGradient(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        pid = pid,
        inner_center = inner_center,
        outer_center = outer_center,
        inner_radius = inner_radius,
        outer_radius = outer_radius,
        stops = [stop[0] for stop in stops],
        stop_colors = [stop[1] for stop in stops],
        )
    cls = self.display.get_resource_class('picture', Picture)
    return cls(self.display, pid, owner = 1)


class CreateConicalGradient(rq.Request):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(36),
        rq.RequestLength(),
        rq.Picture('pid'),
        rq.Object('center', PointFix),
        Fixed('angle'),
        rq.LengthOf(('stops', 'stop_colors'), 4),
        rq.List('stops', FixedObj),
        rq.List('stop_colors', Color),
        )

def create_conical_gradient(self, center, angle, *stops):
    pid = self.display.allocate_resource_id()
    CreateConicalGradient(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        pid = pid,
        center = center,
        angle = angle,
        stops = [stop[0] for stop in stops],
        stop_colors = [stop[1] for stop in stops],
        )
    cls = self.display.get_resource_class('picture', Picture)
    return cls(self.display, pid, owner = 1)


class Picture(resource.Resource):
    __picture__ = resource.Resource.__resource__

    def change(self, **keys):
        ChangePicture(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            values = keys,
            )

    def set_clip_rectangles(self, clip_x_origin, clip_y_origin, *rectangles):
        SetPictureClipRectangles(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            clip_x_origin = clip_x_origin,
            clip_y_origin = clip_y_origin,
            rectangles = rectangles,
            )

    def set_transform(self, transform):
        SetPictureTransform(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            transform = transform,
            )

    def set_filter(self, filter, *values):
        SetPictureFilter(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            filter = filter,
            values = values,
            )

    def fill_rectangles(self, op, color, *rects):
        FillRectangles(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            dst = self,
            color = color,
            rects = rects,
            )

    def create_cursor(self, x, y):
        cid = self.display.allocate_resource_id()
        CreateCursor(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            cid = cid,
            source = self,
            x = x,
            y = y,
            )
        cls = self.display.get_resource_class('cursor', cursor.Cursor)
        return cls(self.display, cid, owner = 1)

    def add_traps(self, off_x, off_y, *trapezoids):
        AddTraps(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            off_x = off_x,
            off_y = off_y,
            trapezoids = trapezoids,
            )

    def free(self):
        FreePicture(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            picture = self,
            )


    def composite(self, op, src, mask, src_x, src_y, mask_x, mask_y, dst_x, dst_y, width, height):
        Composite(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            mask = mask,
            dst = self,
            src_x = src_x,
            src_y = src_y,
            mask_x = mask_x,
            mask_y = mask_y,
            dst_x = dst_x,
            dst_y = dst_y,
            width = width,
            height = height,
            )

    def scale(self, src, color_scale, alpha_scale, src_x, src_y, dst_x, dst_y, width, height):
        Scale(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            src = src,
            dst = self,
            color_scale = color_scale,
            alpha_scale = alpha_scale,
            src_x = src_x,
            src_y = src_y,
            dst_x = dst_x,
            dst_y = dst_y,
            width = width,
            height = height
            )

    def trapezoids(self, op, src, mask_format, src_x, src_y, *traps):
        Trapezoids(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            src_x = src_x,
            src_y = src_y,
            traps = traps,
            )

    def triangles(self, op, src, mask_format, src_x, src_y, *triangles):
        Triangles(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            src_x = src_x,
            src_y = src_y,
            triangles = triangles,
            )

    def tri_strip(self, op, src, mask_format, src_x, src_y, *points):
        TriStrip(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            src_x = src_x,
            src_y = src_y,
            points = points,
            )

    def tri_fan(self, op, src, mask_format, src_x, src_y, *points):
        TriFan(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            src_x = src_x,
            src_y = src_y,
            points = points,
            )

    def composite_glyphs_8(self, op, src, mask_format, glyphset, src_x, src_y, *glyphcmds):
        CompositeGlyphs8(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            glyphset = glyphset,
            src_x = src_x,
            src_y = src_y,
            glyphcmds = glyphcmds,
            )

    def composite_glyphs_16(self, op, src, mask_format, glyphset, src_x, src_y, *glyphcmds):
        CompositeGlyphs16(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            glyphset = glyphset,
            src_x = src_x,
            src_y = src_y,
            glyphcmds = glyphcmds,
            )

    def composite_glyphs_32(self, op, src, mask_format, glyphset, src_x, src_y, *glyphcmds):
        CompositeGlyphs32(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            op = op,
            src = src,
            dst = self,
            mask_format = mask_format,
            glyphset = glyphset,
            src_x = src_x,
            src_y = src_y,
            glyphcmds = glyphcmds,
            )

    def composite_glyphs(self, op, src, mask_format, glyphset, src_x, src_y, *glyphcmds):
        max_glyph = 0
        for glyphcmd in glyphcmds:
            if type(glyphcmd) is types.TupleType:
                deltax, deltay, glyphs = glyphcmd
            elif type(glyphcmd) is types.DictType or isinstance(glyphcmd, rq.DictWrapper):
                glyphs = glyphcmd['glyphs']
            else:
                glyphs = []

            if glyphs:
                glyphs = max(glyphs)
            else:
                glyphs = 0

            max_glyph = max(max_glyph, glyphs)

        if max_glyph < 256:
            func = self.composite_glyphs_8
        elif max_glyph < 65536:
            func = self.composite_glyphs_16
        else:
            func = self.composite_glyphs_32

        func(op, src, mask_format, glyphset, src_x, src_y, *glyphcmds)


class GlyphSet(resource.Resource):
    __glyphset__ = resource.Resource.__resource__

    def reference(self):
        gsid = self.display.allocate_resource_id()
        ReferenceGlyphSet(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            gsid = gsid,
            existing = self,
            )
        cls = self.display.get_resource_class('glyphset', GlyphSet)
        return cls(self.display, gsid, owner = 1)

    def free(self):
        FreeGlyphSet(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            glyphset = self,
            )

    def add_glyphs(self, *glyphs):
        AddGlyphs(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            glyphset = self,
            glyphids = [glyph[0] for glyph in glyphs],
            glyphs = [glyph[1] for glyph in glyphs],
            images = ''.join(glyph[2] for glyph in glyphs),
            )

    def free_glyphs(self, *glyphs):
        FreeGlyphs(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            glyphset = self,
            glyphs = glyphs,
            )


def init(disp, info):
    disp.extension_add_method('display', 'xrender_query_version', query_version)
    disp.extension_add_method('display', 'xrender_query_pict_formats', query_pict_formats)
    disp.extension_add_method('display', 'xrender_query_pict_index_values', query_pict_index_values)
    disp.extension_add_method('drawable', 'xrender_query_filters', query_filters)
    disp.extension_add_method('drawable', 'xrender_create_picture', create_picture)
    disp.extension_add_method('display', 'xrender_create_glyph_set', create_glyph_set)
    disp.extension_add_method('display', 'xrender_create_anim_cursor', create_anim_cursor)
    disp.extension_add_method('display', 'xrender_create_solid_fill', create_solid_fill)
    disp.extension_add_method('display', 'xrender_create_linear_gradient', create_linear_gradient)
    disp.extension_add_method('display', 'xrender_create_radial_gradient', create_radial_gradient)
    disp.extension_add_method('display', 'xrender_create_conical_gradient', create_conical_gradient)

