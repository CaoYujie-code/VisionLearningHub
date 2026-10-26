"""Run a real exercise module with standard imports, under the IDE debugger."""
import argparse
import importlib
import json
from pathlib import Path
import sys

from learning.engine import fixture, compact_value, preview, write_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--lesson', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    sys.path.insert(0, str(root))
    folder = Path(args.output).resolve(); folder.mkdir(parents=True, exist_ok=True)
    image, params, _ = fixture(args.lesson, 17, folder)
    module = importlib.import_module('exercises.' + args.lesson)
    result = module.solve(image, params)
    print(json.dumps(compact_value(result), ensure_ascii=False, indent=2))
    write_image(folder / 'output.png', preview(args.lesson, image, params, result))
    print('输出图片：', folder / 'output.png')


if __name__ == '__main__':
    main()
