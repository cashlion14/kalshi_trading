from PIL import Image, ImageGrab
import pytesseract as ocr
import re


ss_region = (150,210, 250, 270)
ss_img = ImageGrab.grab(ss_region)

num = str(ocr.image_to_string(ss_img))

temp = re.findall(r'\d+', num)
res = list(map(int, temp))
SAPVal = int(''.join([str(x) for x in res]))
print(SAPVal)

# ss_img.show()