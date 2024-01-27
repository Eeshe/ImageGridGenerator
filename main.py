import threading
import random

from PIL import Image
from os import listdir
from time import time, sleep
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


# This class allows the user to create margins, paddings, etc for each individual grid column/row
class GridElementModifier:

    def __init__(self, affected_rows: list, affected_columns: list, top_margin: int = 0, right_margin: int = 0,
                 bottom_margin: int = 0, left_margin: int = 0):
        self.affected_rows = affected_rows
        self.affected_columns = affected_columns
        self.top_margin = top_margin
        self.right_margin = right_margin
        self.bottom_margin = bottom_margin
        self.left_margin = left_margin


# Randomly picks an image file from the input directory.
def pick_random_image_file(used_images: list) -> str | None:
    image_files = listdir(INPUT_DIRECTORY)
    if not image_files:
        return None

    for attempt in range(100):
        image_file = INPUT_DIRECTORY + image_files[random.randint(0, len(image_files) - 1)]
        if image_file in used_images:
            continue

        return image_file

    return None


# General settings
INPUT_DIRECTORY = "/media/HDD/Pictures/ImageGridGenerator/Input"
RESOLUTION = (5760, 10688)
TOTAL_GENERATIONS = 40
OUTPUT_DIRECTORY = "/media/HDD/Pictures/ImageGridGenerator/Output"

# Uniform Grid
GRID_DIMENSIONS = (4, 4)
GRID_ELEMENT_MODIFIERS = [
    # GridElementModifier([], [1, 3], top_margin=200, bottom_margin=200),
    GridElementModifier([], [0], right_margin=200),
    GridElementModifier([], [3], left_margin=200),
    GridElementModifier([0], [], bottom_margin=200),
    GridElementModifier([3], [], top_margin=200),
    # GridElementModifier([], [0, 2], left_margin=100, right_margin=100,),
]

RANDOM_GRID_DIMENSIONS_OPTIONS = [
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
    (6, 6),
    (7, 7)
]

# The amount of px the script can randomly use for top, right, bottom or left margin.
RANDOM_ELEMENT_MODIFIER_OPTIONS = [
    0,
    100,
    200
]

# VaryingSizeGrid
TOP_GRID_MARGIN = 25
RIGHT_GRID_MARGIN = 25
BOTTOM_GRID_MARGIN = 25
LEFT_GRID_MARGIN = 25
GRID_MARGIN_COLOR = (0, 0, 255)

TOP_IMG_MARGIN = 25
RIGHT_IMG_MARGIN = 25
BOTTOM_IMG_MARGIN = 25
LEFT_IMG_MARGIN = 25
IMG_MARGIN_COLOR = (255, 0, 0)


# Applies the passed margins to the passed image.
def _apply_margins(image: Image, top: int, right: int, bottom: int, left: int, color: tuple):
    total_margin_width = left + right
    total_margin_height = top + bottom
    margin_image = Image.new('RGB', (image.width, image.height), color)
    image = image.resize((image.width - total_margin_width, image.height - total_margin_height))
    margin_image.paste(image, (left, top))

    return margin_image


class VaryingSizeGrid:

    def __init__(self, dimensions: tuple, top_grid_margin: int = 0, right_grid_margin: int = 0,
                 bottom_grid_margin: int = 0, left_grid_margin: int = 0, grid_margin_color: tuple = (0, 0, 0),
                 top_img_margin: int = 0, right_img_margin: int = 0, bottom_img_margin: int = 0,
                 left_img_margin: int = 0, img_margin_color: tuple = (0, 0, 0)):
        self.width = dimensions[0]
        self.height = dimensions[1]
        self.used_images = []
        self.used_pixels = []
        self.top_grid_margin = top_grid_margin
        self.right_grid_margin = right_grid_margin
        self.bottom_grid_margin = bottom_grid_margin
        self.left_grid_margin = left_grid_margin
        self.grid_margin_color = grid_margin_color
        self.top_img_margin = top_img_margin
        self.right_img_margin = right_img_margin
        self.bottom_img_margin = bottom_img_margin
        self.left_img_margin = left_img_margin
        self.img_margin_color = img_margin_color

    # Search the closest x pixel that would limit the pasting of an image.
    def search_closest_limit(self, x: int, y: int) -> int:
        for pixel_range in self.used_pixels:
            if y not in pixel_range[1]:
                continue
            if x > pixel_range[0][-1]:
                continue

            return pixel_range[0][0]

        return self.width

    # Applies the configured grid margins to the passed image.
    def apply_grid_margins(self, image: Image) -> Image:
        return _apply_margins(image, self.top_grid_margin, self.right_grid_margin, self.bottom_grid_margin,
                              self.left_grid_margin, self.grid_margin_color)

    # Applies the configured image margins to the passed image.
    def apply_image_margins(self, image: Image) -> Image:
        return _apply_margins(image, self.top_img_margin, self.right_img_margin, self.bottom_img_margin,
                              self.left_img_margin, self.img_margin_color)

    # Picks a random image that fits within the remaining space.
    def pick_random_fitting_image(self, current_x: int, current_y: int):
        remaining_x = self.search_closest_limit(current_x, current_y) - current_x
        print(f"{self.height} - {current_y}")
        remaining_y = self.height - current_y
        image_files = listdir(INPUT_DIRECTORY)
        if not image_files or remaining_y == 0:
            return None

        random.shuffle(image_files)
        for image_file in image_files:
            if image_file in self.used_images:
                continue

            self.used_images.append(image_file)
            image = Image.open(f"{INPUT_DIRECTORY}/{image_file}")
            x_difference_percentage = abs((image.width - self.left_grid_margin - self.right_grid_margin / remaining_x))
            y_difference_percentage = abs((image.height - self.top_grid_margin - self.bottom_grid_margin / remaining_y))
            if image.width > remaining_x or x_difference_percentage > 0.5:
                # Resize X
                new_x = remaining_x
                new_y = min(remaining_y, int(remaining_x / (image.width / image.height)))
            elif image.height > remaining_y or y_difference_percentage > 0.5:
                # Resize Y
                new_x = min(remaining_x, int(remaining_y / (image.width / image.height)))
                new_y = remaining_y
            else:
                return image

            image = image.resize((new_x, new_y))
            return image

        return None

    # Attempts to find the lowest empty y pixel corresponding to the passed x pixel.
    def find_next_empty_y_pixel(self, x: int):
        empty_y_pixel = 0
        for pixel_ranges in self.used_pixels:
            if x not in pixel_ranges[0]:
                continue

            empty_y_pixel = max(empty_y_pixel, pixel_ranges[1][-1] + 1)

        return empty_y_pixel + self.top_grid_margin

    # Generates the grid image.
    def generate(self):
        grid_image = Image.new('RGB', (self.width, self.height))
        grid_image = self.apply_grid_margins(grid_image)
        y = 0
        while y < self.height:
            x = self.left_grid_margin
            while x < self.width:
                y = self.find_next_empty_y_pixel(x)
                used_pixel = False
                for pixel_ranges in self.used_pixels:
                    if y not in pixel_ranges[1]:
                        continue
                    if x not in pixel_ranges[0]:
                        continue

                    used_pixel = True
                    break
                if used_pixel:
                    x += 1
                    continue

                image = self.pick_random_fitting_image(x, y)
                if image is None:
                    break

                image = self.apply_image_margins(image)
                self.used_pixels.append((range(x, x + image.width), range(y, y + image.height)))
                grid_image.paste(image, (x, y))
                x += image.width

        return grid_image


# Creates the image grid.
def create_image_grid(grid_dimensions: tuple, resolution: tuple, grid_element_modifiers=None):
    if grid_element_modifiers is None:
        grid_element_modifiers = []

    columns = grid_dimensions[0]
    rows = grid_dimensions[1]

    target_width = resolution[0]
    target_height = resolution[1]

    used_images = []
    grid_image = Image.new('RGB', (target_width, target_height))
    for column in range(columns):
        for row in range(rows):
            image_file = pick_random_image_file(used_images)
            if image_file is None:
                return None

            top_margin = 0
            right_margin = 0
            bottom_margin = 0
            left_margin = 0
            image_width = target_width / columns
            image_height = target_height / rows
            for element_modifier in grid_element_modifiers:
                if row in element_modifier.affected_rows or column in element_modifier.affected_columns:
                    top_margin = element_modifier.top_margin
                    bottom_margin = element_modifier.bottom_margin
                    left_margin = element_modifier.left_margin
                    right_margin = element_modifier.right_margin

            image_width -= (left_margin + right_margin) / columns
            image_height -= (top_margin + bottom_margin) / rows

            used_images.append(image_file)
            image = Image.open(image_file)
            image = image.resize((max(1, int(image.width * (image_width / image.width))),
                                  max(1, int(image.height * (image_height / image.height)))))

            x = column * image_width
            if left_margin != 0:
                x += left_margin
            y = row * image_height
            if top_margin != 0:
                y += top_margin
            grid_image.paste(image, (int(x), int(y)))

    return grid_image


# Generates and saves an image grid with the passed parameters. Used for threading.
def generate_and_save_grid(generation_count: int):
    image = create_image_grid(GRID_DIMENSIONS, RESOLUTION, GRID_ELEMENT_MODIFIERS)
    image.save(f'{OUTPUT_DIRECTORY}/{generation_count}.jpg')


# Generates and saves a varying size grid with the passed parameters. Used for threading.
def generate_and_save_varying_size_grid(generation_count: int):
    image = VaryingSizeGrid(
        RESOLUTION,
        top_grid_margin=TOP_GRID_MARGIN,
        right_grid_margin=BOTTOM_GRID_MARGIN,
        bottom_grid_margin=RIGHT_GRID_MARGIN,
        left_grid_margin=LEFT_GRID_MARGIN,
        grid_margin_color=GRID_MARGIN_COLOR,
        top_img_margin=TOP_IMG_MARGIN,
        right_img_margin=RIGHT_IMG_MARGIN,
        bottom_img_margin=BOTTOM_IMG_MARGIN,
        left_img_margin=LEFT_IMG_MARGIN,
        img_margin_color=IMG_MARGIN_COLOR).generate()
    image.save(f'{OUTPUT_DIRECTORY}/{generation_count}.jpg')


def main() -> None:
    with tqdm(total=TOTAL_GENERATIONS) as progress_bar:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(generate_and_save_varying_size_grid, generation_count) for generation_count in
                       range(1, TOTAL_GENERATIONS + 1)]

            for future in as_completed(futures):
                future.result()
                progress_bar.update(1)


if __name__ == '__main__':
    main()
