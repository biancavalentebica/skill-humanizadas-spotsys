import sys, glob, os
from PIL import Image, ImageDraw
pasta, padrao, saida, z = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
fs = sorted(glob.glob(os.path.join(pasta, padrao)))
ims = [Image.open(p).convert('RGB') for p in fs]; ims = [i.resize((int(i.width*z), int(i.height*z)), Image.LANCZOS) for i in ims]
W = 2000; x = y = 0; rowh = 0; pos = []
for im in ims:
    if x + im.width > W: x = 0; y += rowh + 22; rowh = 0
    pos.append((x, y + 20)); x += im.width + 10; rowh = max(rowh, im.height)
sh = Image.new('RGB', (W, y + rowh + 22), (150, 150, 150)); d = ImageDraw.Draw(sh)
for p, im, (x, y) in zip(fs, ims, pos): sh.paste(im, (x, y)); d.text((x, y - 16), os.path.basename(p)[-8:-4], fill=(200, 0, 0))
sh.save(saida); print(len(ims), sh.size)
