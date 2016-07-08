import requests
import json
import jsonschema
import os
from binascii import b2a_hex
import PIL.Image as Image
import io

from collections import OrderedDict
from collections import defaultdict
import pdfminer
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator

from annotation_schema import page_schema


def determine_image_type (stream_first_4_bytes):
    file_type = None
    bytes_as_hex = b2a_hex(stream_first_4_bytes)
    if bytes_as_hex.startswith('ffd8'):
        file_type = '.jpeg'
    elif bytes_as_hex == '89504e47':
        file_type = '.png'
    elif bytes_as_hex == '47494638':
        file_type = '.gif'
    elif bytes_as_hex.startswith('424d'):
        file_type = '.bmp'
    return file_type


def save_image(lt_image, page_n, book, images_folder):
    result = None
    if lt_image.stream:
        file_stream = lt_image.stream.get_rawdata()
        if file_stream:
            file_ext = determine_image_type(file_stream[0:4])
            if file_ext:
                file_name = book + '_' + str(page_n) + file_ext
                if write_file(images_folder, file_name, file_stream, flags='wb'):
                    result = file_name
    return result


def scale_and_save_image(pdf_page_image, page_n, book, images_folder, scale_factor):
    result = None
    file_ext = '.jpeg'
    file_name = book + '_' + str(page_n) + file_ext
    file_stream = scale_image(pdf_page_image, scale_factor)
    if file_stream.size:
        file_stream.save(images_folder + '/' + file_name, format="JPEG")

    return result


def write_file(folder, filename, filedata, flags='w'):
    result = False
    if os.path.isdir(folder):
        file_obj = open(os.path.join(folder, filename), flags)
        file_obj.write(filedata)
        file_obj.close()
        result = True
    return result


def scale_image(pdf_page_image, scale_factor):
    page_image = Image.open(io.BytesIO(pdf_page_image.stream.get_rawdata()))
    img_dim = tuple([int(dim*scale_factor) for dim in page_image.size])
    page_image.thumbnail(img_dim, Image.ANTIALIAS)
    return page_image.convert('L')


def record_image_size(pdf_page_image):
    page_image = Image.open(io.BytesIO(pdf_page_image))
    img_dim = page_image.size
    return img_dim


def write_image_file(layout, page_n, book, dir_name, scale_factor=0):
    figure_detections = [detection for detection in layout._objs if type(detection) == pdfminer.layout.LTFigure][0]
    page_image = figure_detections._objs[0]
    if not scale_factor:
        save_image(page_image, page_n, book, dir_name)
    else:
        scale_and_save_image(page_image, page_n, book, dir_name, scale_factor)
    return


def write_annotation_file(ocr_results, page_n, book, annotations_folder):

    def point_to_tuple(box):
        return tuple(OrderedDict(sorted(box.items())).values())

    def get_bbox_tuples(detection):
        return map(point_to_tuple, detection['rectangle'])

    ids = 1
    annotation = defaultdict(defaultdict)
    try:
        for box in ocr_results['detections']:
            box_id = 'T' + str(ids)
            bounding_rectangle = get_bbox_tuples(box)
            annotation['text'][box_id] = {
                "box_id": box_id,
                "category": "unlabeled",
                "contents": box['value'],
                "score": box['score'],
                "rectangle": bounding_rectangle,
                "source": {
                    "type": "object",
                    "$schema": "http://json-schema.org/draft-04/schema",
                    "additionalProperties": False,
                    "properties": [
                        {"book_source": book},
                        {"page_n": page_n}
                    ]
                }
            }
            ids += 1
    except KeyError:
        annotation['text'] = {}

    annotation['figure'] = {}
    annotation['relationship'] = {}

    validator = jsonschema.Draft4Validator(page_schema)
    validator.validate(json.loads(json.dumps(annotation)))

    file_ext = ".json"
    file_path = annotations_folder + '/' + book + '_' + str(page_n) + file_ext
    with open(file_path, 'wb') as f:
        json.dump(annotation, f)
    return


def query_vision_ocr(image_url, merge_boxes=False, include_merged_components=False, as_json=True):
    print image_url
    req = requests.get(image_url)
    tpi = Image.open(io.BytesIO(req.content))
    print(tpi.info, tpi.size, tpi.size[0]*tpi.size[1])
    api_entry_point = 'http://vision-ocr.dev.allenai.org/v1/ocr'
    header = {'Content-Type': 'application/json'}
    request_data = {
        'url': image_url,
        # 'maximumSizePixels': max_pix_size,
        'mergeBoxes': merge_boxes,
        'includeMergedComponents': include_merged_components
    }

    json_data = json.dumps(request_data)
    response = requests.post(api_entry_point, data=json_data, headers=header)
    print(response.reason)
    json_response = json.loads(response.content.decode())
    if as_json:
        response = json_response
    return response


def process_book(pdf_file, page_range, line_overlap,
                 char_margin,
                 line_margin,
                 word_margin,
                 boxes_flow):
    line_overlap = 0.5
    source_dir = 'pdfs/'
    book_name = pdf_file.replace('.pdf', '')
    laparams = LAParams(line_overlap, char_margin, line_margin, word_margin, boxes_flow)

    with open(source_dir + pdf_file, 'r') as fp:
        parser = PDFParser(fp)
        document = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        for page_n, page in enumerate(PDFPage.create_pages(document)):
            if not page_range or (page_range[0] <= page_n <= page_range[1]):
                interpreter.process_page(page)
                layout = device.get_result()
                write_image_file(layout, page_n, book_name, 'smaller_page_images', 0.66)


def assemble_url(page_number, book_name, base_url):
    return base_url + book_name.replace('+', '%2B') + '_' + str(page_number) + '.jpeg'


def check_response(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response
    else:
        return False


def perform_ocr(pdf_file, annotation_dir, (start_n, stop_n)):
    book_name = pdf_file.replace('.pdf', '')

    base_url = 'https://s3-us-west-2.amazonaws.com/ai2-vision-turk-data/textbook-annotation-test/smaller-page-images/'

    page_n = start_n
    while page_n <= stop_n:
        file_ext = ".json"
        file_path = annotation_dir + '/' + book_name + '_' + str(page_n) + file_ext
        if not os.path.isfile(file_path):

            print(book_name, page_n)
            try:
                print(assemble_url(page_n, book_name, base_url))
                ocr_response = query_vision_ocr(assemble_url(page_n, book_name, base_url))
                write_annotation_file(ocr_response, page_n, book_name, annotation_dir)
            except ValueError:
                print('ocr service error')
        page_n += 1
