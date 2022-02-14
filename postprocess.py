# Copyright 2021 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""YoloV5 310 infer."""
import os
import argparse
import time
import ast
import numpy as np
from pycocotools.coco import COCO
from src.logger import get_logger
from src.util import DetectionEngine

parser = argparse.ArgumentParser('yolov5 postprocess')

# dataset related
parser.add_argument('--per_batch_size', default=1, type=int, help='batch size for per gpu')

# logging related
parser.add_argument('--log_path', type=str, default='outputs/', help='checkpoint save location')

# detect_related
parser.add_argument('--nms_thresh', type=float, default=0.6, help='threshold for NMS')
parser.add_argument('--ann_file', type=str, default='', help='path to annotation')
parser.add_argument('--ignore_threshold', type=float, default=0.001, help='threshold to throw low quality boxes')

parser.add_argument('--dataset_path', type=str, default='', help='path of image dataset')
parser.add_argument('--result_files', type=str, default='./result_Files', help='path to 310 infer result path')
parser.add_argument('--multi_label', type=ast.literal_eval, default=True, help='whether to use multi label')
parser.add_argument('--multi_label_thresh', type=float, default=0.1, help='threshold to throw low quality boxes')

args, _ = parser.parse_known_args()


if __name__ == "__main__":
    start_time = time.time()

    args.outputs_dir = os.path.join(args.log_path,
                                    datetime.datetime.now().strftime('%Y-%m-%d_time_%H_%M_%S'))
    args.logger = get_logger(args.outputs_dir, 0)

    # init detection engine
    detection = DetectionEngine(args, args.ignore_threshold)

    coco = COCO(args.ann_file)
    result_path = args.result_files

    files = os.listdir(args.dataset_path)

    for file in files:
        img_ids_name = file.split('.')[0]
        img_id_ = int(np.squeeze(img_ids_name))
        imgIds = coco.getImgIds(imgIds=[img_id_])
        img = coco.loadImgs(imgIds[np.random.randint(0, len(imgIds))])[0]
        image_shape = ((img['width'], img['height']),)
        img_id_ = (np.squeeze(img_ids_name),)

        result_path_0 = os.path.join(result_path, img_ids_name + "_0.bin")
        result_path_1 = os.path.join(result_path, img_ids_name + "_1.bin")
        result_path_2 = os.path.join(result_path, img_ids_name + "_2.bin")

        output_small = np.fromfile(result_path_0, dtype=np.float32).reshape(1, 20, 20, 3, 85)
        output_me = np.fromfile(result_path_1, dtype=np.float32).reshape(1, 40, 40, 3, 85)
        output_big = np.fromfile(result_path_2, dtype=np.float32).reshape(1, 80, 80, 3, 85)

        detection.detect([output_small, output_me, output_big], args.per_batch_size, image_shape, img_id_)

    args.logger.info('Calculating mAP...')
    detection.do_nms_for_results()
    result_file_path = detection.write_result()
    args.logger.info('result file path: {}'.format(result_file_path))
    eval_result = detection.get_eval_result()

    cost_time = time.time() - start_time
    args.logger.info('\n=============coco 310 infer reulst=========\n' + eval_result)
    args.logger.info('testing cost time {:.2f}h'.format(cost_time / 3600.))
