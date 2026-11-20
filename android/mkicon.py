from PIL import Image, ImageDraw
import os
src = Image.open(r"D:\AI\1exe_icon.png").convert("RGBA")
side = 512
# 居中补成正方形，背景用暗色圆角
canvas = Image.new("RGBA", (side, side), (0,0,0,0))
w,h = src.size
scale = min(side*0.86/w, side*0.86/h)
nw,nh = int(w*scale), int(h*scale)
img = src.resize((nw,nh), Image.LANCZOS)
# 圆角底板
base = Image.new("RGBA",(side,side),(0,0,0,0))
d = ImageDraw.Draw(base)
d.rounded_rectangle([0,0,side-1,side-1], radius=112, fill=(14,19,27,255))
base.alpha_composite(img, ((side-nw)//2, (side-nh)//2))
out = r"D:\AI\android-build\icon_master.png"
base.save(out)
sizes = {"mdpi":48,"hdpi":72,"xhdpi":96,"xxhdpi":144,"xxxhdpi":192}
root = r"D:\AI\android-build\app\res"
for dpi,s in sizes.items():
    p = os.path.join(root, "mipmap-"+dpi)
    os.makedirs(p, exist_ok=True)
    base.resize((s,s), Image.LANCZOS).save(os.path.join(p,"ic_launcher.png"))
    print(dpi, s, os.path.join(p,"ic_launcher.png"))
print("master", out, base.size)
