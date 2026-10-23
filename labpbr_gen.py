"""LabPBR 1.3 _n / _s generator for pixel-art Minecraft textures (16x16 source texels -> 128x128 output).

_n : R,G = normal (DirectX, flat = 127), B = AO, A = height
_s : R = smoothness, G = F0 / metal id, B = porosity / SSS, A = emission (255 = none)

Everything is computed on a 16x16 grid of source texels; each texel becomes an 8x8 block.
"""
import os
import numpy as np
from PIL import Image

CELL = 8          # output pixels per source texel
GRID = 16         # source texels per side
# height step (A units) across a texel boundary -> normal offset on the higher side (measured from the reference pack)
EDGE_TABLE = [(0, 0), (4, 5), (8, 9), (12, 13), (16, 18), (20, 54), (24, 54), (32, 58),
              (40, 62), (48, 71), (56, 73), (64, 77), (128, 100)]


# ---------- input ----------
def load_texels(path):
    """Read a base-colour texture (16x16, or NxN with N a multiple of 16) as a 16x16 RGBA float array.
    For upscaled textures the centre pixel of every cell is used."""
    a = np.asarray(Image.open(path).convert('RGBA')).astype(float)
    if a.shape[0] != a.shape[1] or a.shape[0] % GRID:
        raise ValueError(f'{path}: expected a square texture whose side is a multiple of 16, got {a.shape[:2]}')
    n = a.shape[0] // GRID
    c = (n - 1) // 2
    return a[c::n, c::n][:GRID, :GRID]


def luminance(tex):
    """sRGB values used directly, no linearisation."""
    return 0.299 * tex[..., 0] + 0.587 * tex[..., 1] + 0.114 * tex[..., 2]


def remap(L, lo, hi, invert=False, mask=None):
    """Linearly map luminance (min..max over `mask`) to lo..hi."""
    sel = L if mask is None else L[mask]
    a, b = sel.min(), sel.max()
    t = np.zeros_like(L) if b == a else (L - a) / (b - a)
    t = np.clip(1 - t if invert else t, 0, 1)
    return lo + t * (hi - lo)


def up(t):
    return np.kron(t, np.ones((CELL, CELL)))


# ---------- _n ----------
def height_from_colour(tex, lower, upper=255, step=4):
    """Brighter = higher. Quantised so that values sit on upper - k*step. Never below 1."""
    h = remap(luminance(tex), lower, upper)
    h = upper - np.round((upper - h) / step) * step
    return np.clip(h, max(lower, 1), upper)


def edge_strength(delta):
    xs = [a for a, _ in EDGE_TABLE]
    ys = [b for _, b in EDGE_TABLE]
    return float(np.round(np.interp(delta, xs, ys)))


def narrow_normals(H, min_edge=0, gain=1.0):
    """1px-wide normal on the HIGHER texel's side of every boundary where height differs.
    min_edge / gain raise the strength for low-contrast textures so the edges stay visible."""
    N = GRID * CELL
    R = np.zeros((N, N))
    G = np.zeros((N, N))

    def es(d):
        return max(edge_strength(d) * gain, min_edge)

    for ty in range(GRID):
        for tx in range(GRID):
            h = H[ty, tx]
            y0, x0 = ty * CELL, tx * CELL
            d = h - H[ty, (tx + 1) % GRID]
            if d > 0:
                R[y0:y0 + CELL, x0 + CELL - 1] += es(d)     # surface falls to the right -> R > 127
            d = h - H[ty, (tx - 1) % GRID]
            if d > 0:
                R[y0:y0 + CELL, x0] -= es(d)
            d = h - H[(ty + 1) % GRID, tx]
            if d > 0:
                G[y0 + CELL - 1, x0:x0 + CELL] += es(d)     # surface falls downward -> G > 127 (DirectX)
            d = h - H[(ty - 1) % GRID, tx]
            if d > 0:
                G[y0, x0:x0 + CELL] -= es(d)
    return R, G


def _shift(m, dy, dx, wrap):
    s = np.roll(np.roll(m, dy, 0), dx, 1)
    if not wrap:
        if dy == 1: s[0, :] = False
        if dy == -1: s[-1, :] = False
        if dx == 1: s[:, 0] = False
        if dx == -1: s[:, -1] = False
    return s


def wide_normals(bump, levels=(19,), wrap=True):
    """'Wide normals': whole 8x8 texels on the border of a raised structure tilt outward.
    bump   : 16x16 bool mask of the raised structure(s).
    levels : tilt per ring from the outside in, e.g. (19,) or (29, 19, 9). Usual values 9 / 19 / 29.
    wrap   : True if the texture tiles (structures continue across the border);
             False to treat the texture border as the structure's edge (e.g. a bevel round the whole block)."""
    bump = np.asarray(bump, bool)
    Rt = np.zeros((GRID, GRID))
    Gt = np.zeros((GRID, GRID))
    m = bump.copy()
    for lv in levels:
        left = m & ~_shift(m, 0, 1, wrap)
        right = m & ~_shift(m, 0, -1, wrap)
        top = m & ~_shift(m, 1, 0, wrap)
        bottom = m & ~_shift(m, -1, 0, wrap)
        Rt += lv * (right.astype(int) - left.astype(int))
        Gt += lv * (bottom.astype(int) - top.astype(int))
        m = m & ~(left | right | top | bottom)
    return up(Rt), up(Gt)


def cylinder_gradient(centre=63.7, half_width=67.6, bulge=29.9, axis='x'):
    """Per-pixel (continuous) elliptical gradient that makes a face read as a cylinder (log sides).
    axis='x' -> returns an R offset; axis='y' -> use the result as a G offset."""
    n = GRID * CELL
    x = np.arange(n)
    u = np.clip((x - centre) / half_width, -0.999, 0.999)
    s = bulge * u / (half_width * np.sqrt(1 - u * u))
    g = 127 * s / np.sqrt(1 + s * s)
    return np.tile(g, (n, 1)) if axis == 'x' else np.tile(g[:, None], (1, n))


def hbao(H, radius=12, strength=0.6, dirs=16, depth_px=0.03):
    """Horizon-based AO on the stepped height map. Parameters were fitted to the reference pack
    (mean abs error about 2/255); it is an approximation, not Substance Designer's HBAO node."""
    h = up(H) * depth_px
    occ = np.zeros_like(h)
    for k in range(dirs):
        ang = 2 * np.pi * k / dirs
        dx, dy = np.cos(ang), np.sin(ang)
        hor = np.zeros_like(h)
        for r in range(1, radius + 1):
            sx, sy = int(round(dx * r)), int(round(dy * r))
            if sx == 0 and sy == 0:
                continue
            sh = np.roll(np.roll(h, -sy, 0), -sx, 1)
            hor = np.maximum(hor, (sh - h) / np.hypot(sx, sy) * (1 - (r - 1) / radius))
        occ += hor / np.sqrt(1 + hor * hor)
    return np.clip(1 - strength * occ / dirs, 0, 1) * 255


def build_n(tex, lower, upper=255, step=4, height=None, height_overrides=None,
            bump=None, wide_levels=(19,), wide_wrap=True, cylinder=False,
            min_edge=0, edge_gain=1.0, ao=True, flat=False, flat_ao=False,
            transparent_flat=False, hbao_strength=0.6):
    """Returns (RGBA uint8 image, 16x16 height array).
    height           : optional ready-made 16x16 height array (skips the luminance step).
    height_overrides : list of (16x16 bool mask, value) applied after the luminance step
                       (mortar lines, openings, raised ore grains ...).
    flat             : True for textures that carry no height (plants, glass, cut-outs): A = 255.
                       By default this also drops AO; pass flat_ao=True to keep it.
    flat_ao          : with flat=True, still compute AO from the (unwritten) height map.
                       The reference pack does this for item / entity / armour-layer sprites:
                       A is 255 everywhere (no parallax) while B keeps a light self-shadow.
    transparent_flat : force fully transparent texels to the reference pack's clean values
                       (R=G=127, B=255, A=255). Used for item sprites, whose background must
                       not pick up normals or a silhouette shadow."""
    H = np.array(height, float) if height is not None else height_from_colour(tex, lower, upper, step)
    for mask, value in (height_overrides or []):
        H[np.asarray(mask, bool)] = value
    H = np.clip(H, 1, 255)
    R, G = narrow_normals(H, min_edge, edge_gain)
    if bump is not None:
        wr, wg = wide_normals(bump, wide_levels, wide_wrap)
        R += wr
        G += wg
    if cylinder:
        R += cylinder_gradient()
    ln = np.hypot(R, G)                                # keep |xy| <= 125 so z can be reconstructed (corners where two edges meet)
    k = np.where(ln > 125, 125 / np.maximum(ln, 1e-9), 1.0)
    R, G = R * k, G * k
    A = np.full((GRID * CELL,) * 2, 255.0) if flat else up(H)
    B = hbao(H, strength=hbao_strength) if (ao and (not flat or flat_ao)) else np.full((GRID * CELL,) * 2, 255.0)
    if transparent_flat:
        tr = up(tex[..., 3]) <= 0
        R[tr] = 0.0
        G[tr] = 0.0
        B[tr] = 255.0
        A[tr] = 255.0
    out = np.dstack([127 + R, 127 + G, B, A]).round().clip(0, 255).astype('uint8')
    out[..., 3] = np.maximum(out[..., 3], 1)          # height 0 breaks POM in some shaders
    return Image.fromarray(out, 'RGBA'), H


# ---------- _s ----------
def build_s(tex, r_range, g=10, b=0, r_invert=False, regions=None, emission=None,
            clear_alpha=False):
    """r_range  : (lo, hi) smoothness range for the material; luminance is mapped linearly into it. No HBAO overlay.
    g, b     : constant F0/metal id and porosity/SSS value for the main material.
    regions  : list of dicts for texels whose material differs (metal fittings, ore grains ...):
               {'mask': 16x16 bool, 'r_range': (lo, hi), 'g': int, 'b': int (optional), 'r_invert': bool (optional)}
    emission : list of dicts {'mask': 16x16 bool, 'value': int} or {'mask': ..., 'range': (lo, hi)}
               (range maps luminance inside the mask). 254 = strongest; 255 means "no emission".
    clear_alpha : force fully transparent texels to R=G=B=0, A=255 (the reference pack's item sprites).
               Note this only zeroes R/G/B; emission A stays 255, never 0."""
    L = luminance(tex)
    main = np.ones((GRID, GRID), bool)
    for reg in (regions or []):
        main &= ~np.asarray(reg['mask'], bool)
    if not main.any():
        main[:] = True
    R = remap(L, r_range[0], r_range[1], r_invert, main)
    Gc = np.full((GRID, GRID), float(g))
    Bc = np.full((GRID, GRID), float(b))
    A = np.full((GRID, GRID), 255.0)
    for reg in (regions or []):
        m = np.asarray(reg['mask'], bool)
        if not m.any():
            continue
        R[m] = remap(L, reg['r_range'][0], reg['r_range'][1], reg.get('r_invert', False), m)[m]
        Gc[m] = reg['g']
        if 'b' in reg:
            Bc[m] = reg['b']
    for em in (emission or []):
        m = np.asarray(em['mask'], bool)
        if not m.any():
            continue
        if 'range' in em:
            A[m] = remap(L, em['range'][0], em['range'][1], False, m)[m]
        else:
            A[m] = em['value']
        A[m] = np.clip(A[m], 1, 254)
    if clear_alpha:
        tr = tex[..., 3] <= 0
        R[tr] = 0.0
        Gc[tr] = 0.0
        Bc[tr] = 0.0
        A[tr] = 255.0
    out = np.dstack([up(R), up(Gc), up(Bc), up(A)]).round().clip(0, 255).astype('uint8')
    return Image.fromarray(out, 'RGBA')


# ---------- output ----------
def save_with_channels(img, path, channel_dir=None):
    """Save the combined texture plus one greyscale PNG per channel (<name>_R.png ... <name>_A.png)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    cdir = channel_dir or os.path.dirname(os.path.abspath(path))
    os.makedirs(cdir, exist_ok=True)
    for i, c in enumerate('RGBA'):
        img.getchannel(i).save(os.path.join(cdir, f'{stem}_{c}.png'))


def check_n(img):
    """Basic LabPBR sanity checks for a generated _n. Returns a list of problems (empty = OK)."""
    a = np.asarray(img.convert('RGBA')).astype(float)
    problems = []
    if a[..., 3].min() < 1:
        problems.append('height contains 0 (minimum should be 1)')
    x = (a[..., 0] - 127) / 127
    y = (a[..., 1] - 127) / 127
    if (x * x + y * y).max() > 1.0:
        problems.append('normal xy longer than 1 somewhere (z cannot be reconstructed)')
    return problems


def check_s(img):
    """Basic checks for a generated _s. Returns a list of problems (empty = OK)."""
    a = np.asarray(img.convert('RGBA'))
    problems = []
    if img.mode != 'RGBA':
        problems.append('_s must be saved as RGBA so that non-emissive pixels carry A = 255')
    if (a[..., 3] == 0).any():
        problems.append('emission (A) contains 0; non-emissive pixels must be 255, never 0')
    g = a[..., 1]
    if ((g >= 238) & (g <= 254)).any():
        problems.append('G uses 238-254, which LabPBR leaves undefined')
    return problems


def mask_from_rows(rows, on='#'):
    """Build a 16x16 bool mask from 16 strings of 16 characters, e.g. '####....####....'."""
    if len(rows) != GRID or any(len(r) != GRID for r in rows):
        raise ValueError('mask needs 16 rows of 16 characters')
    return np.array([[ch == on for ch in r] for r in rows])
