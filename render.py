#
# Xlib.ext.render -- Rendering extension module
#
#    Copyright (C) 2011-2012 Aleksi Torhamo <aleksi@torhamo.net>
#
"""Rendering extension"""

from Xlib import X
from Xlib.protocol import rq, structs
from Xlib.xobject import drawable, resource, cursor

extname = 'RENDER'

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
Fixed = rq.Card32 # XXX: 16bit + 16bit, fixed-point
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

def query_version(self, major, minor):
    return QueryVersion(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        major_version = major,
        minor_version = minor,
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


# XXX: Untested, my X server returned BadImplementation
class QueryFilters(rq.ReplyRequest):
    _request = rq.Struct(
        rq.Card8('opcode'),
        rq.Opcode(3),
        rq.RequestLength(),
        rq.Drawable('drawable'),
        )

    _reply = rq.Struct(
        rq.List('filters', rq.String8),
        rq.List('aliases', rq.Card16),
        )

def query_filters(self):
    return QueryFilters(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        drawable = self,
        )


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
        rq.Picture('pid'),
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
        rq.Picture('pid'),
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

# XXX: method of picture
def composite(self, op, src, mask, dst, src_x, src_y, mask_x, mask_y, dst_x, dst_y, width, height):
    return Composite(
        display = self.display,
        opcode = self.display.get_extension_major(extname),
        op = op,
        src = src,
        mask = mask,
        dst = dst,
        src_x = src_x,
        src_y = src_y,
        mask_x = mask_x,
        mask_y = mask_y,
        dst_x = dst_x,
        dst_y = dst_y,
        width = width,
        height = height,
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


class Picture(resource.Resource):
    __picture__ = resource.Resource.__resource__

    def change(self, **keys):
        ChangePicture(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            pid = self,
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

    def free(self):
        FreePicture(
            display = self.display,
            opcode = self.display.get_extension_major(extname),
            pid = self,
            )


def init(disp, info):
    disp.extension_add_method('display',
                              'render_query_version',
                              query_version)

    disp.extension_add_method('display',
                              'render_query_pict_formats',
                              query_pict_formats)

    disp.extension_add_method('display',
                              'render_query_pict_index_values',
                              query_pict_index_values)

    disp.extension_add_method('drawable',
                              'render_query_filters',
                              query_filters)

    disp.extension_add_method('drawable',
                              'create_picture',
                              create_picture)

    disp.extension_add_method('display',
                              'render_composite',
                              composite)

    disp.extension_add_method('display',
                              'create_anim_cursor',
                              create_anim_cursor)

