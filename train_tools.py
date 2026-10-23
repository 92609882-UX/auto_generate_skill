"""Helpers for the calibration ("training") rounds: look at a base texture on a labelled grid,
read what the reference pack did, and compare a generated texture with the reference channel by channel."""
import numpy as np
from PIL import Image, ImageDraw
import labpbr_gen as lg


def grid_str(mask, on='#', off='.'):
    """16 rows of 16 characters, with row/column indices (hex) so both sides can name a texel."""
    head = '   ' + ''.join('%X' % i for i in range(16))
    return '\n'.join([head] + ['%X  ' % y + ''.join(on if v else off for v in row) for y, row in enumerate(np.asarray(mask, bool))])


def value_grid_str(arr, width=4):
    """16x16 integer grid (heights, tilts ...) with indices."""
    head = '    ' + ''.join(('%X' % i).rjust(width) for i in range(16))
    return '\n'.join([head] + ['%X   ' % y + ''.join(str(int(round(v))).rjust(width) for v in row) for y, row in enumerate(arr)])


def preview(base_path, out_png, scale=40):
    """Enlarged base colour with texel grid lines and hex indices, for discussing individual texels."""
    tex = lg.load_texels(base_path)[..., :3].astype('uint8')
    im = Image.fromarray(tex).resize((16 * scale, 16 * scale), Image.NEAREST)
    canvas = Image.new('RGB', (16 * scale + 24, 16 * scale + 24), 'white')
    canvas.paste(im, (24, 24))
    d = ImageDraw.Draw(canvas)
    for i in range(17):
        d.line([(24 + i * scale, 24), (24 + i * scale, 24 + 16 * scale)], fill=(0, 0, 0))
        d.line([(24, 24 + i * scale), (24 + 16 * scale, 24 + i * scale)], fill=(0, 0, 0))
    for i in range(16):
        d.text((24 + i * scale + scale // 2 - 3, 6), '%X' % i, fill='black')
        d.text((8, 24 + i * scale + scale // 2 - 5), '%X' % i, fill='black')
    canvas.save(out_png)
    return out_png


def reference_n(n_path):
    """What the reference _n contains, per texel:
    height  : 16x16 A values
    wide_r, wide_g : 16x16 whole-texel tilt (value at the cell centre minus 127) -> the 'wide normal' layer
    bump_edge : texels that carry any wide tilt"""
    a = np.asarray(Image.open(n_path).convert('RGBA')).astype(float)
    n = a.shape[0] // 16
    c = (n - 1) // 2
    cen = a[c::n, c::n][:16, :16]
    wide_r, wide_g = cen[..., 0] - 127, cen[..., 1] - 127
    return dict(height=cen[..., 3], wide_r=wide_r, wide_g=wide_g, bump_edge=(wide_r != 0) | (wide_g != 0))


def reference_s(s_path):
    """Per-texel values of the reference _s (cell centre): r, g, b, a as 16x16 arrays."""
    a = np.asarray(Image.open(s_path).convert('RGBA')).astype(float)
    n = a.shape[0] // 16
    c = (n - 1) // 2
    cen = a[c::n, c::n][:16, :16]
    return dict(r=cen[..., 0], g=cen[..., 1], b=cen[..., 2], a=cen[..., 3])


def compare(mine, ref_path, out_png=None, tile=200):
    """Mean absolute difference per channel, share of pixels within +-2, and (optionally) a side-by-side sheet:
    for each channel, left = generated, right = reference."""
    m = np.asarray(mine.convert('RGBA')).astype(float)
    r = np.asarray(Image.open(ref_path).convert('RGBA').resize(mine.size, Image.NEAREST)).astype(float)
    d = np.abs(m - r)
    stats = {ch: dict(mean_abs_diff=round(float(d[..., i].mean()), 2), within_2=round(float((d[..., i] <= 2).mean()), 3))
             for i, ch in enumerate('RGBA')}
    if out_png:
        sheet = Image.new('RGB', (tile * 8, tile + 16), 'white')
        dr = ImageDraw.Draw(sheet)
        for i, ch in enumerate('RGBA'):
            lo = min(m[..., i].min(), r[..., i].min())
            hi = max(m[..., i].max(), r[..., i].max())
            for j, (src, lab) in enumerate([(m, 'generated'), (r, 'reference')]):
                g = ((src[..., i] - lo) / max(1.0, hi - lo) * 255).astype('uint8')
                x = (i * 2 + j) * tile
                sheet.paste(Image.fromarray(g).resize((tile - 4, tile - 4), Image.NEAREST), (x, 16))
                dr.text((x + 2, 2), f'{ch} {lab}', fill='black')
        sheet.save(out_png)
    return stats


def mask_agreement(proposed, reference):
    """How well a proposed 16x16 mask matches a reference mask: share of equal texels, plus the two kinds of miss."""
    p, r = np.asarray(proposed, bool), np.asarray(reference, bool)
    return dict(agree=round(float((p == r).mean()), 3), only_in_proposed=int((p & ~r).sum()), only_in_reference=int((~p & r).sum()))
