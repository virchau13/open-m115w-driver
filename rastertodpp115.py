#!/usr/bin/env python3


from collections import namedtuple
from datetime import datetime
import struct, sys

if len(sys.argv) < 7 or len(sys.argv) > 8:
    # we have an incorrect number of arguments (we need either 6 or 7 arguments, but since $0 exists, the bounds change by 1)
    sys.stderr.buffer.write(b'Usage: rastertodpp115 <job-id> <username> <title> <num-copies> <options> [file]')
    sys.exit(1)

CupsRas3 = namedtuple(
    # Documentation at https://www.cups.org/doc/spec-raster.html
    'CupsRas3',
    'MediaClass MediaColor MediaType OutputType AdvanceDistance AdvanceMedia Collate CutMedia Duplex HWResolutionH ' 'HWResolutionV ImagingBoundingBoxL ImagingBoundingBoxB ImagingBoundingBoxR ImagingBoundingBoxT '
    'InsertSheet Jog LeadingEdge MarginsL MarginsB ManualFeed MediaPosition MediaWeight MirrorPrint '
    'NegativePrint NumCopies Orientation OutputFaceUp PageSizeW PageSizeH Separations TraySwitch Tumble cupsWidth '
    'cupsHeight cupsMediaType cupsBitsPerColor cupsBitsPerPixel cupsBitsPerLine cupsColorOrder cupsColorSpace '
    'cupsCompression cupsRowCount cupsRowFeed cupsRowStep cupsNumColors cupsBorderlessScalingFactor cupsPageSizeW '
    'cupsPageSizeH cupsImagingBBoxL cupsImagingBBoxB cupsImagingBBoxR cupsImagingBBoxT cupsInteger1 cupsInteger2 '
    'cupsInteger3 cupsInteger4 cupsInteger5 cupsInteger6 cupsInteger7 cupsInteger8 cupsInteger9 cupsInteger10 '
    'cupsInteger11 cupsInteger12 cupsInteger13 cupsInteger14 cupsInteger15 cupsInteger16 cupsReal1 cupsReal2 '
    'cupsReal3 cupsReal4 cupsReal5 cupsReal6 cupsReal7 cupsReal8 cupsReal9 cupsReal10 cupsReal11 cupsReal12 '
    'cupsReal13 cupsReal14 cupsReal15 cupsReal16 cupsString1 cupsString2 cupsString3 cupsString4 cupsString5 '
    'cupsString6 cupsString7 cupsString8 cupsString9 cupsString10 cupsString11 cupsString12 cupsString13 cupsString14 '
    'cupsString15 cupsString16 cupsMarkerType cupsRenderingIntent cupsPageSizeName'
)


def read_ras3(rdata):
    if not rdata:
        raise ValueError('No data received')

    # Check for magic word (either big-endian or little-endian)
    magic = struct.unpack('@4s', rdata[0:4])[0]
    if magic != b'RaS3' and magic != b'3SaR':
        raise ValueError("This is not in RaS3 format")
    rdata = rdata[4:]  # Strip magic word
    pages = []

    while rdata:  # Loop over all pages
        struct_data = struct.unpack(
            '@64s 64s 64s 64s I I I I I II IIII I I I II I I I I I I I I II I I I I I I I I I I I I I '
            'I I I f ff ffff IIIIIIIIIIIIIIII ffffffffffffffff 64s 64s 64s 64s 64s 64s 64s 64s 64s 64s '
            '64s 64s 64s 64s 64s 64s 64s 64s 64s',
            rdata[0:1796]
        )
        data = [
            # Strip trailing null-bytes of strings
            b.decode().rstrip('\x00') if isinstance(b, bytes) else b
            for b in struct_data
        ]
        header = CupsRas3._make(data)

        # Read image data of this page into a bytearray
        imgdata = rdata[1796:1796 + (header.cupsWidth * header.cupsHeight * header.cupsBitsPerPixel // 8)]
        pages.append((header, imgdata))

        # Remove this page from the data stream, continue with the next page
        rdata = rdata[1796 + (header.cupsWidth * header.cupsHeight * header.cupsBitsPerPixel // 8):]

    return pages

pages = read_ras3(sys.stdin.buffer.read())

# argv fmt
# <job> <user> <title> <num-copies> <options> [<filename>]
sys.stdout.buffer.write("""12345X@PJL
@PJL SET HOLD=OFF
@PJL SET JOBNAME="{}"
@PJL SET USERNAME="{}"
@PJL JOB NAME="{}"
@PJL PRINTLOG ITEM = 1,PRINTER
@PJL PRINTLOG ITEM = 2,{}
@PJL PRINTLOG ITEM = 3,{}
@PJL PRINTLOG ITEM = 4,Linux
@PJL SET STRINGCODESET=HPROMAN8
@PJL SET LOGINUSER="{}"
@PJL SET RESOLUTION = 600
@PJL SET ECONOMODE = OFF
@PJL SET LESSPAPERCURL=OFF
@PJL SET FIXINTENSITYUP=OFF
@PJL SET TRANSFERLEVELUP=ON
@PJL TRANSFERLEVEL=0
@PJL SET MEDIATYPE=REGULAR
@PJL DEFAULT AUTOSLEEP = ON
@PJL DEFAULT TIMEOUTSLEEP = 1
@PJL SET JOBTIME="{}"
@PJL SET ORIENTATION = PORTRAIT
@PJL SET PAPER = A4
@PJL SET PAGEPROTECT = AUTO
@PJL ENTER LANGUAGE = PCL
""".format(sys.argv[1], sys.argv[2], sys.argv[1], datetime.now().strftime("%a,%d %b %Y %H:%M:%S"), sys.argv[2], sys.argv[2], datetime.now().strftime("%Y%m%d%H%M%S"))) 

for i, datatuple in enumerate(pages):
    (header, imgdata) = datatuple
    if header.cupsColorSpace != 0 or header.cupsNumColors != 1:
        raise ValueError('Invalid color space, only greyscale is supported')
