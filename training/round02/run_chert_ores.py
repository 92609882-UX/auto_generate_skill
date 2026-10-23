import os, numpy as np, labpbr_gen as lg, train_tools as tt
from PIL import Image
CH='/mnt/user-data/uploads/natures_spirit_pbr/assets/natures_spirit/textures/block/chert_%s_ore.png'
REF='/mnt/user-data/uploads/mcproperty/05‘s_resourcepacks/!!§r§f§l 零雾构想 v5003 §7- 2025-10-02 §0/assets/minecraft/textures/block/%s_ore%s.png'
OUT='/mnt/user-data/outputs/round02'
ORES=['copper','emerald','gold','iron','lapis','redstone']
BASE_LUM=(107.0,158.0)                       # 所有 chert 矿石底矿的亮度范围（固定，保证底矿一致）
BASE=[(189,132,83),(173,115,73),(203,148,92),(181,123,78),(196,141,90),(163,106,67),(148,95,57),(157,102,63)]
def is_base(t): return np.array([[tuple(int(v) for v in t[y,x,:3]) in BASE for x in range(16)] for y in range(16)])
def fixed_remap(L,lo,hi,a=BASE_LUM[0],b=BASE_LUM[1]): return lo+np.clip((L-a)/(b-a),0,1)*(hi-lo)
def ref_table(ore):
    t=lg.load_texels(REF%(ore,''))[...,:3].astype(int); s=tt.reference_s(REF%(ore,'_s'))
    gm=(s['g']!=0)|(s['a']<255)
    return t,s,gm
def go(ore):
    tex=lg.load_texels(CH%ore); rgb=tex[...,:3].astype(int); L=lg.luminance(tex)
    grain=~is_base(rgb)
    rt,rs,rg=ref_table(ore)
    refcols=rt[rg]
    # 钻石颗粒同款做法：底矿 207-231(台阶8) ，颗粒 247-255(台阶4，按颗粒自身亮度)
    H=np.zeros((16,16))
    hb=fixed_remap(L,207,231); H[~grain]=(231-np.round((231-hb)/8)*8)[~grain]
    g=lg.remap(L,247,255,mask=grain); H[grain]=(255-np.round((255-g)/4)*4)[grain]
    n,H=lg.build_n(tex,lower=207,height=H,bump=None,edge_gain=1.4,hbao_strength=1.2)
    # _s ：底矿统一 R 52-103、G10、B0、A255；颗粒逐块取参考包同色颗粒的值（A 减半）
    R=fixed_remap(L,52,103); G=np.full((16,16),10.); B=np.zeros((16,16)); A=np.full((16,16),255.)
    info={}
    for y,x in zip(*np.nonzero(grain)):
        c=rgb[y,x]; d=np.abs(refcols-c).sum(1); k=d.argmin()
        near=(np.abs(refcols-refcols[k]).sum(1)<=6)
        sel=[(yy,xx) for (yy,xx) in zip(*np.nonzero(rg))][:]
        idx=np.array(sel)[near]
        r=np.median([rs['r'][i,j] for i,j in idx]); gg=np.median([rs['g'][i,j] for i,j in idx]); b=np.median([rs['b'][i,j] for i,j in idx]); a=np.median([rs['a'][i,j] for i,j in idx])
        if 238<=gg<=254: gg=255                      # 参考包用了 LabPBR 未定义的 G，改成 255
        R[y,x]=r; G[y,x]=gg; B[y,x]=b; A[y,x]=int(a/2+0.5)
        info[tuple(c)]=(int(d[k]),int(r),int(gg),int(b),int(a),int(A[y,x]))
    s=Image.fromarray(np.dstack([lg.up(R),lg.up(G),lg.up(B),lg.up(A)]).round().clip(0,255).astype('uint8'),'RGBA')
    pn,ps=lg.check_n(n),lg.check_s(s)
    d=f'{OUT}/{ore}'; os.makedirs(d,exist_ok=True)
    lg.save_with_channels(n,f'{d}/chert_{ore}_ore_n.png',f'{d}/channels'); lg.save_with_channels(s,f'{d}/chert_{ore}_ore_s.png',f'{d}/channels')
    sh=Image.new('RGB',(4*260,2*260),'white')
    for r_,img in enumerate([n,s]):
        for i in range(4): sh.paste(img.getchannel(i).convert('RGB').resize((256,256),Image.NEAREST),(i*260,r_*260))
    sh.save(f'{d}/chert_{ore}_ore_8channels_sheet.png')
    print('==',ore,'grains',grain.sum(),'check',pn,ps); print(tt.grid_str(grain))
    for c,v in sorted(info.items()): print(' ',c,'refdist/R/G/B/A_ref/A_half',v)
for o in ORES: go(o)
