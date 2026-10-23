import numpy as np, labpbr_gen as lg, train_tools as tt
from PIL import Image
SRC='/mnt/user-data/uploads/natures_spirit_pbr/assets/natures_spirit/textures/block/chert_diamond_ore.png'
OUT='/mnt/user-data/outputs/round01_v2'
tex=lg.load_texels(SRC)
L=lg.luminance(tex)
grain=tex[...,2]>tex[...,0]+10            # 钻石颗粒：偏青蓝色的块
print(tt.grid_str(grain), grain.sum())
# 高度：底矿 207-231(台阶8)，钻石 247-255(台阶4，按亮度)，钻石整体抬高
H=np.zeros((16,16))
base=lg.remap(L,207,231,mask=~grain)
H[~grain]=(231-np.round((231-base)/8)*8)[~grain]
g=lg.remap(L,247,255,mask=grain)
H[grain]=(255-np.round((255-g)/4)*4)[grain]
print(tt.value_grid_str(H))
n,H=lg.build_n(tex,lower=207,height=H,bump=None,edge_gain=1.4,hbao_strength=1.2)
# _s：钻石颗粒采用参考包 diamond_ore_s 的取值
emis=[]
for lo,hi,v in [(0,130,24),(130,175,35),(175,220,41),(220,256,48)]:
    emis.append(dict(mask=grain&(L>=lo)&(L<hi),value=v))
s=lg.build_s(tex,r_range=(52,103),g=10,b=0,
    regions=[dict(mask=grain,r_range=(228,232),g=219,b=0)],emission=emis)
print(lg.check_n(n),lg.check_s(s))
lg.save_with_channels(n,f'{OUT}/chert_diamond_ore_n.png',f'{OUT}/channels')
lg.save_with_channels(s,f'{OUT}/chert_diamond_ore_s.png',f'{OUT}/channels')
sheet=Image.new('RGB',(4*260,2*260+4),'white')
for r,img in enumerate([n,s]):
    for i in range(4):
        sheet.paste(img.getchannel(i).convert('RGB').resize((256,256),Image.NEAREST),(i*260,r*260))
sheet.save('/tmp/w/sheet2.png')
a=np.asarray(s); print(np.unique(a[...,0]),np.unique(a[...,3]))
