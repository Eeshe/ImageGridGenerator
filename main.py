import threading
import random

from PIL import Image
from os import listdir
from time import time
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


class VaryingSizeGrid:

    def __init__(self, dimensions: tuple):
        self.width = dimensions[0]
        self.height = dimensions[1]
        self.used_images = []
        self.used_pixels = []

    # Picks a random image that fits within the remaining space.
    def pick_random_fitting_image(self, current_x: int, current_y: int):
        remaining_x = self.width - current_x
        remaining_y = self.height - current_y
        for attempt in range(100):
            image_file = pick_random_image_file(self.used_images)
            image = Image.open(image_file)
            if image.width > remaining_x or image.height > remaining_y:
                continue

            self.used_images.append(image_file)
            return image

        return None

    # Attempts to find the lowest empty x pixel corresponding to the passed pixel.
    def find_next_empty_x_pixel(self, y: int):
        empty_x_pixel = 0
        for pixel_ranges in self.used_pixels:
            if y not in pixel_ranges[1]:
                continue
            empty_x_pixel = max(empty_x_pixel, pixel_ranges[0][-1])

        return empty_x_pixel

    # Attempts to find the lowest empty y pixel corresponding to the passed x pixel.
    def find_next_empty_y_pixel(self, x: int):
        empty_y_pixel = 0
        for pixel_ranges in self.used_pixels:
            if x not in pixel_ranges[0]:
                continue

            empty_y_pixel = max(empty_y_pixel, pixel_ranges[1][-1])

        return empty_y_pixel

    # Generates the grid image.
    def generate(self):
        grid_image = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        x = 0
        while x < self.width:
            y = self.find_next_empty_y_pixel(x)
            print(f"X: {x} Y: {y}")

            image = self.pick_random_fitting_image(x, y)
            if image is None:
                if x >= self.width - 1000:
                    break
                if y >= self.height - 200:
                    y = 0
                x = self.find_next_empty_x_pixel(y) + 1
                continue

            self.used_pixels.append((range(x, x + image.width), range(y, y + image.height)))
            grid_image.paste(image, (x, y))

        return grid_image


INPUT_DIRECTORY = "/media/HDD/Pictures/ImageGridGenerator/Input/"
GRID_DIMENSIONS = (4, 4)
RESOLUTION = (2160, 3840)
TOTAL_GENERATIONS = 50
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

OUTPUT_DIRECTORY = "/media/HDD/Pictures/ImageGridGenerator/Output/"


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


def main() -> None:
    start = time()
    image = VaryingSizeGrid((7680, 8640)).generate()
    end = time()
    print(f"GRID GENERATION TOOK {end - start}ms")
    image.save(f'{OUTPUT_DIRECTORY}/output.jpg')

    # with tqdm(total=TOTAL_GENERATIONS) as progress_bar:
    #     with ThreadPoolExecutor(max_workers=20) as executor:
    #         futures = [executor.submit(generate_and_save_grid, generation_count) for generation_count in
    #                    range(1, TOTAL_GENERATIONS + 1)]
    #
    #         for future in as_completed(futures):
    #             future.result()
    #             progress_bar.update(1)


if __name__ == '__main__':
    main()
