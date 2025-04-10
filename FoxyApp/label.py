from PIL import Image, ImageDraw, ImageFont
from FoxyApp import app
from FoxyApp.foxfireutility import friday
import os


def label(user, receipt, pickup, total, dt, comment, volume):
    #  declare variables
    name2 = f"{user.name}\nTotal:${total}"
    farm_address = "Foxfire Farm LLC\n2107 South Fork Ridge Rd. Liberty KY 42539"
    pickup = f"{pickup}"
    receipt = f"{receipt}"
    comment = f"Comment: {comment}"
    balance = "Balance:$______"
    date = friday()
    volume = f"Box Size: {volume}"
    filename = os.path.join(app.root_path, "static/labels", f"{user.id}{dt}.jpg")
    #  font sizes
    fnt = ImageFont.truetype('DejaVuSans.ttf', 25)
    name_font = ImageFont.truetype('DejaVuSans.ttf', 80)
    balance_font = ImageFont.truetype('DejaVuSans.ttf', 80)
    receipt_font = ImageFont.truetype('DejaVuSans.ttf', 30)
    boxsize_font = ImageFont.truetype('DejaVuSans.ttf', 30)
    pickup_font = ImageFont.truetype('DejaVuSans.ttf', 60)
    date_font = ImageFont.truetype('DejaVuSans.ttf', 60)
    # create new image
    image = Image.new(mode = "RGB", size = (696,1000), color = "white")   # height x width
    draw = ImageDraw.Draw(image)

    #  declare widths and heights for all text
    farm_width, farm_height = draw.textsize(farm_address, font=fnt)
    name_width, name_height = draw.textsize(name2, font=name_font)
    balance_width, balance_height = draw.textsize(balance, font=balance_font)
    pickup_width, pickup_height = draw.textsize(pickup, font=pickup_font)
    comment_width, comment_height = draw.textsize(comment, font=fnt)
    receipt_width, receipt_height = draw.textsize(receipt, font=receipt_font)
    boxsize_width, boxsize_height = draw.textsize(volume, font=boxsize_font)
    date_width, date_height = draw.textsize(receipt, font=receipt_font)

    #  add height of "Balance" line if customer is prepaid
    if user.prepaid == "0":
        balance_height = 0


    draw.text((10,10), f"{farm_address}", font=fnt, fill=(0,0,0))

    text_next_height = 10 + farm_height + 10
    draw.text((10, text_next_height), name2, font=name_font, fill=(0, 0, 0))

    if user.prepaid == "1":
        text_next_height = 10 + farm_height + name_height + 20
        draw.text((10, text_next_height), balance, font=balance_font, fill=(0, 0, 0))

    text_next_height = 10 + farm_height + name_height + balance_height + 20
    draw.text((10, text_next_height), receipt, font=receipt_font, fill=(0, 0, 0))

    text_next_height = 10 + farm_height + name_height + balance_height + receipt_height + 20
    draw.text((10, text_next_height), comment, font=fnt, fill=(0, 0, 0))

    text_next_height = 10 + farm_height + name_height + balance_height + receipt_height + comment_height + 20
    draw.text((10, text_next_height), pickup, font=pickup_font, fill=(0, 0, 0))

    text_next_height = 10 + farm_height + name_height + balance_height + receipt_height + comment_height + pickup_height + 20
    draw.text((10, text_next_height), date, font=date_font, fill=(0, 0, 0))

    text_next_height = 10 + farm_height + name_height + balance_height + receipt_height + comment_height + pickup_height + date_height + 20
    draw.text((10, text_next_height), volume, font=boxsize_font, fill=(0, 0, 0))

    image.save(filename)

    #from brother_ql.conversion import convert
    #from brother_ql.backends.helpers import send
    #from brother_ql.raster import BrotherQLRaster
    #import os
    ##  Print label
    #im = Image.open(filename)
    #backend = 'pyusb'  # 'pyusb', 'linux_kernal', 'network'
    #model = 'QL-800'  # your printer model.
    #printer = 'usb://0x04f9:0x209b/000F3G135939'  # Get these values from the Windows usb driver filter.  Linux/Raspberry Pi uses '/dev/usb/lp0'.
#
    #qlr = BrotherQLRaster(model)
    #qlr.exception_on_warning = True
#
    #instructions = convert(
    #    qlr=qlr,
    #    images=[im],  # Takes a list of file names or PIL objects.
    #    label='62',
    #    rotate='90',  # 'Auto', '0', '90', '270'
    #    threshold=70.0,  # Black and white threshold in percent.
    #    dither=False,
    #    compress=False,
    #    red=False,  # Only True if using Red/Black 62 mm label tape.
    #    dpi_600=False,
    #    hq=True,  # False for low quality.
    #    cut=True
    #)

    #send(instructions=instructions, printer_identifier=printer, backend_identifier=backend, blocking=True)
    #os.remove(filename)