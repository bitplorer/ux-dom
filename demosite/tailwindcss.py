# Copyright (c) 2022 ux_dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

from demosite import settings
from ux_dom import TailwindCommand

tailwind = TailwindCommand(
    file_path=__file__,
    webassets=settings.webassets,
    # input_css=settings.INPUT_CSS_FILE,
    # output_css=settings.OUTPUT_CSS_FILE,
    minify=not settings.DEBUG,
)

if __name__ == "__main__":
    tailwind.run()
