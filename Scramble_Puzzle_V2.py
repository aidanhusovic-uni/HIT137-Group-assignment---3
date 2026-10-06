import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk

# Transfer function class
class Transfer:  # Provides a shared description and apply and undo structure for transfers

    def __init__(self, description):

        self.description = description

    def apply(self, target):

        raise NotImplementedError('Override this method in subclasses')

    def undo(self, target):

        raise NotImplementedError('Override this method in subclasses')

    def __str__(self):

        return self.description

# Swap transfer function class
class SwapTransfer(Transfer):  # Swaps two tiles by exchanging their positions in the tile list

    def __init__(self, pos_a, pos_b):

        super().__init__(f'Swap Tiles {pos_a} and {pos_b}')
        self.pos_a = pos_a
        self.pos_b = pos_b

    def apply(self, tiles):

        tiles[self.pos_a], tiles[self.pos_b] = tiles[self.pos_b], tiles[self.pos_a]

    def undo(self, tiles):

        self.apply(tiles)

# Rotate transfer class
class RotateTransfer(Transfer):  # Rotates images by linking angles to OpenCV rotation flags
    ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}

    def __init__(self, angle):

        if angle not in self.ROTATIONS:
            raise ValueError('Angle must be one of 90, 180 or 270 degrees.')

        super().__init__(f'Rotate Image by {angle} degrees')
        self.angle = angle

    def apply(self, image):

        return cv2.rotate(image, self.ROTATIONS[self.angle])

    def undo(self, image):

        return cv2.rotate(image, self.ROTATIONS[(360 - self.angle) % 360])

    @classmethod

    def apply_angle(cls, image, angle):  # Returns an unchanged copy for 0 degrees, otherwise rotates the image
        if angle == 0:

            return image.copy()

        return cv2.rotate(image, cls.ROTATIONS[angle])

# Flip transfer class
class FlipTransfer(Transfer):  # Flips images by choosing the correct OpenCV flip code

    def __init__(self, direction):

        if direction not in ['horizontal', 'vertical']:

            raise ValueError("Direction must be 'horizontal' or 'vertical'.")

        description = 'Flip tile Horizontally' if direction == 'horizontal' else 'Flip tile Vertically'

        super().__init__(description)

        self.direction = direction

    def apply(self, image):

        flip_n = 1 if self.direction == 'horizontal' else 0

        return cv2.flip(image, flip_n)

    def undo(self, image):

        return self.apply(image)

# Tile class
class Tile:

    def __init__(self, tile_id, image):  # Stores the tile ID and original and current images

        self.__tile_id = tile_id
        self.__original_image = image.copy()
        self.__current_image = image.copy()

        self.__rotation = 0
        self.__flipped_horizontal = False
        self.__flipped_vertical = False

    @property

    def tile_id(self):
    
        return self.__tile_id #Returns the private tile ID through a controlled property

    @property

    def current_image(self):

        return self.__current_image  #Returns the private current image through a controlled property

    @property

    def rotation(self):

        return self.__rotation #Returns the private rotation value through a controlled property

    @property

    def flipped_horizontal(self): 

        return self.__flipped_horizontal #Returns the private horizontal flip value through a controlled property

    @property

    def flipped_vertical(self):

        return self.__flipped_vertical #Returns the private vertical flip value through a controlled property

    def rotate_cw(self):  # Rotates the image clockwise and updates the rotation value

        self.__current_image = RotateTransfer.apply_angle(self.__current_image, 90)
        self.__rotation = (self.__rotation + 90) % 360

    def flip_horizontal(self):  # Applies a horizontal flip and toggles the flip value

        self.__current_image = FlipTransfer('horizontal').apply(self.__current_image)
        self.__flipped_horizontal = not self.__flipped_horizontal

    def flip_vertical(self):  # Applies a vertical flip and toggles the flip value

        self.__current_image = FlipTransfer('vertical').apply(self.__current_image)
        self.__flipped_vertical = not self.__flipped_vertical

    def is_correct_orientation(self):  # Compares the current and original images

        return np.array_equal(self.__current_image, self.__original_image)

    def reset_orientation(self):  # Restores the original image and orientation values

        self.__current_image = self.__original_image.copy()
        self.__rotation = 0
        self.__flipped_horizontal = False
        self.__flipped_vertical = False

# Main puzzle function class
class ImagePuzzle:

    MAX_SCREEN_WIDTH = 450
    MAX_SCREEN_HEIGHT = 450
    MAX_HINTS = 3

    #Main def 
    def __init__(self, grid_size=3):  #Creates the puzzle values and starts the game with no image or tiles

        self.__grid_size = grid_size
        self.__original_image = None
        self.__tiles = []
        self.__transformations = []
        self.__moves = 0
        self.__hints_used = 0
        self.__solved = False

    @property 
    def grid_size(self):  #Returns the private grid size through a controlled property
        return self.__grid_size

    @grid_size.setter
    def grid_size(self, value):  #Allows the grid size to be replaced safely

        self.__grid_size = value

    @property 
    def original_image(self):  #Returns the private original image through a controlled property

        return self.__original_image

    @property 
    def tiles(self):  #Returns the private tile list through a controlled property

        return self.__tiles

    @property 
    def moves(self):  #Returns the private move count through a controlled property

        return self.__moves

    @property 
    def hints_used(self):  #Returns the private hint count through a controlled property

        return self.__hints_used

    @hints_used.setter
    def hints_used(self, value):  #Allows the hint count to be updated safely

        self.__hints_used = value

    @property 
    def solved(self):  #Returns the private solved value through a controlled property

        return self.__solved

    def load_image(self, file_path): #Loads an image by resizing, cropping, tiling and scrambling it

        image = cv2.imread(file_path)

        if image is None: 
            raise ValueError('OpenCV could not read the selected image.')

        image = self.__resize_to_screen(image)
        image = self.__make_square_and_divisible(image)
        self.__original_image = image.copy()

        self.__create_tiles() 
        self.__scramble_tiles() 

        self.__moves = 0
        self.__hints_used = 0
        self.__solved = False

    def __resize_to_screen(self, image):  #Calculates a scale factor and resizes the image using OpenCV

        height, width = image.shape[:2]
        scale = min(self.MAX_SCREEN_WIDTH / width, self.MAX_SCREEN_HEIGHT / height, 1.0)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(image, (new_width, new_height))

    def __make_square_and_divisible(self, image):  #Finds the largest square side length that divides evenly by the grid size

        height, width = image.shape[:2]
        side = min(height, width)
        side = (side // self.__grid_size) * self.__grid_size

        if side < self.__grid_size: 
            raise ValueError('Image is too small for the specified grid size.')

        start_x = (width - side) // 2
        start_y = (height - side) // 2
        return image[start_y:start_y + side, start_x:start_x + side].copy()

    def __create_tiles(self):  #Divides the image into a list of Tile objects

        self.__tiles = []

        tile_height = self.__original_image.shape[0] // self.__grid_size
        tile_width = self.__original_image.shape[1] // self.__grid_size
        tile_id = 0

        for row in range(self.__grid_size):
            for col in range(self.__grid_size):
                y1 = row * tile_height 
                y2 = y1 + tile_height
                x1 = col * tile_width
                x2 = x1 + tile_width
                tile_image = self.__original_image[y1:y2, x1:x2].copy()
                self.__tiles.append(Tile(tile_id, tile_image))
                tile_id += 1

    def __scramble_tiles(self):  #Applies random swaps, rotations and flips to the tiles

        transfer_counts = {3: 6, 4: 12, 5:20} 
        count = transfer_counts.get(self.__grid_size, 6)

        for _ in range(count):
            choice = random.choice(['swap', 'rotate', 'flip'])

            if choice =='swap': 
                pos_a, pos_b = random.sample(range(len(self.__tiles)), 2)
                transfer = SwapTransfer(pos_a, pos_b)
                transfer.apply(self.__tiles)

            elif choice == 'rotate': 
                index = random.randrange(len(self.__tiles))
                angle = random.choice([90, 180, 270])
                transfer = RotateTransfer(angle)

                for _ in range(angle // 90): 
                    self.__tiles[index].rotate_cw()

            else: 
                index = random.randrange(len(self.__tiles))
                direction = random.choice(['horizontal', 'vertical'])
                transfer = FlipTransfer(direction)

                if direction == 'horizontal': 
                    self.__tiles [index].flip_horizontal()
                else:
                    self.__tiles [index].flip_vertical()

            self.__transformations.append(transfer)

    def get_tile_size (self):  #Divides the image width and height by the grid size

        height, width = self.__original_image.shape[:2]
        return (width // self.__grid_size, height // self.__grid_size)

    def assemble_image (self):  #Joins tile images into rows using hstack and stacks the rows using vstack

        rows = []

        for row in range (self.__grid_size):
            row_tiles = [self.__tiles[row * self.__grid_size + col].current_image for col in range(self.__grid_size)]
            rows.append(np.hstack(row_tiles))

        return np.vstack(rows)

    def swap_tiles (self, pos_a, pos_b):  #Exchanges two list positions using tuple unpacking and increases the move count

        self.__tiles[pos_a], self.__tiles[pos_b] = self.__tiles[pos_b], self.__tiles[pos_a]
        self.__moves += 1

    def rotate_tile (self, index):  #Calls the tile rotation method and increases the move count

        self.__tiles[index].rotate_cw()
        self.__moves += 1

    def flip_tile (self, index, direction = 'horizontal'):  #Chooses the horizontal or vertical Tile method and increases the move count

        if direction == 'horizontal':
            self.__tiles[index].flip_horizontal()
        else:
            self.__tiles[index].flip_vertical()
        self.__moves += 1

    def tile_correct (self, index):  #Compares the tile ID with its list position and checks its image

        tile = self.__tiles [index]
        return tile.tile_id == index and tile.is_correct_orientation()

    def tile_incorrect (self):  #Counts every tile that fails the correct-position and image check

        return sum (not self.tile_correct (index) for index in range (len(self.__tiles)))

    def check_solved (self):  #Sets solved to True when the incorrect tile count reaches zero

        self.__solved = self.tile_incorrect() == 0
        return self.__solved

    def hint (self):  #Finds the first tile that fails the correct check and returns both positions

        for current_index in range (len(self.__tiles)):
            if not self.tile_correct(current_index):
                return current_index, self.__tiles [current_index].tile_id
        return None

    def use_hint(self):  # Uses a hint if the puzzle is unsolved and hints remain

        if self.__solved or self.__hints_used >= self.MAX_HINTS:
            return False

        if self.hint() is None:
            return False

        self.__hints_used += 1
        return True

    def solve (self):  #Places each tile into the list position matching its tile ID

        tile_order = [None] * len(self.__tiles)

        for tile in self.__tiles:
            tile_order [tile.tile_id] = tile

        self.__tiles = tile_order

        for tile in self.__tiles:
            tile.reset_orientation()

        self.__moves = 0
        self.__hints_used = 0
        self.__solved = True

# Creating the Key UI features
class PuzzleCreate:

    def __init__(self, root):  # Creates the main window and starting UI values
        self.root = root
        self.root.title('Scramble Puzzle / AIDAN HUSOVIC')
        self.root.configure(bg='#1e1e1e')

        self.puzzle = ImagePuzzle()
        self.selected_tile = None
        self.hint_tile = None
        self.hint_home = None
        self.original_photo = None
        self.puzzle_photo = None

        self.controls()
        self.tile_controls()
        self.build_canvas()
        self.build_status_bar()

    def build_status_bar(self):  # Creates the status bar at the bottom of the window

        self.status_var = tk.StringVar(value='Load an image to begin')
        tk.Label(self.root, textvariable=self.status_var, bg='#121212', fg='#eaeaea', font=('Arial', 10), anchor='w', padx=12, pady=6).pack(fill=tk.X, side=tk.BOTTOM)

    def controls(self):  # Creates the grid selector and main buttons

        control_frame = tk.Frame(self.root, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, padx=12, pady=10)

        tk.Label(control_frame, text='Grid size:', bg='#1e1e1e', fg='#eaeaea', font=('Arial', 11)).pack(side=tk.LEFT)

        self.grid_size_var = tk.StringVar(value='3 x 3')
        ttk.Combobox(control_frame, textvariable=self.grid_size_var, values=['3 x 3', '4 x 4', '5 x 5'], state='readonly', width=8).pack(side=tk.LEFT, padx=(6, 15))

        tk.Button(control_frame, text='Load Image', command=self.load_image, bg='#2a41a8', fg='#ffffff', font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT)

        self.hint_button = tk.Button(control_frame, text='Hint', command=self.use_hint, bg='#2a41a8', fg='#ffffff', font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=12, pady=4)
        self.hint_button.pack(side=tk.LEFT, padx=(15, 0))

        tk.Button(control_frame, text='Solve', command=self.solve_puzzle, bg='#2a41a8', fg='#ffffff', font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT, padx=(10, 0))

    def tile_controls(self):  # Creates the tile action buttons

        frame = tk.LabelFrame(self.root, text='Tile Controls', bg='#1e1e1e', fg='#eaeaea', font=('Arial', 10, 'bold'), padx=10, pady=8)
        frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.selected_tile_var = tk.StringVar(value='')

        tk.Button(frame, text='Rotate Clockwise', command=self.rotate_selected_tile, bg='#2a41a8', fg='#ffffff', font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.LEFT, padx=4)
        tk.Button(frame, text='Flip Horizontally', command=self.flip_selected_tile, bg='#2a41a8', fg='#ffffff', font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.LEFT, padx=4)
        tk.Button(frame, text='Deselect', command=self.deselect_tile, bg='#1e1e1e', fg='#eaeaea', font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=10, pady=4).pack(side=tk.LEFT, padx=4)

    def build_canvas(self):  # Creates the reference and puzzle canvases

        frame = tk.Frame(self.root, bg='#1e1e1e')
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.original_canvas = tk.Canvas(frame, width=ImagePuzzle.MAX_SCREEN_WIDTH, height=ImagePuzzle.MAX_SCREEN_HEIGHT, bg='#0f0f0f', highlightthickness=1, highlightbackground='#4a4a4a')
        self.original_canvas.grid(row=0, column=0, padx=(0, 12))

        self.puzzle_canvas = tk.Canvas(frame, width=ImagePuzzle.MAX_SCREEN_WIDTH, height=ImagePuzzle.MAX_SCREEN_HEIGHT, bg='#0f0f0f', highlightthickness=1, highlightbackground='#4a4a4a')
        self.puzzle_canvas.grid(row=0, column=1)

        self.puzzle_canvas.bind('<Button-1>', self.on_left_click)
        self.puzzle_canvas.bind('<Button-3>', self.on_right_click)
        self.puzzle_canvas.bind('<Shift-Button-1>', self.on_shift_left_click)

        tk.Label(self.root, text='Original image (reference) Puzzle image        (click or use buttons to solve)', bg='#1e1e1e', fg='#a0a0a0', font=('Arial', 10)).pack()

    def load_image(self):  # Opens a file dialog and loads the selected image

        file_path = filedialog.askopenfilename(title='Choose an image', filetypes=[('Image files', '*.jpg *.jpeg *.png *.bmp'), ('All files', '*.*')])

        if not file_path:
            return

        self.puzzle.grid_size = int(self.grid_size_var.get().split('x')[0].strip())

        try:
            self.puzzle.load_image(file_path)
        except Exception as error:
            messagebox.showerror('Image Error', str(error))
            return

        self.selected_tile = None
        self.hint_tile = None
        self.hint_home = None
        self.hint_button.config(state=tk.NORMAL)

        choices = [str(index) for index in range(len(self.puzzle.tiles))]
        self.selected_tile_var.set('')

        self.display_images()
        self.update_status()


    def get_tile_from_click(self, event):  # Finds the tile index from the mouse position

        if self.puzzle.original_image is None or self.puzzle.solved:
            return None

        tile_width, tile_height = self.puzzle.get_tile_size()
        col = event.x // tile_width
        row = event.y // tile_height

        if 0 <= col < self.puzzle.grid_size and 0 <= row < self.puzzle.grid_size:
            return row * self.puzzle.grid_size + col

        return None

    def on_left_click(self, event):  # Selects a tile or swaps it with a second selected tile

        index = self.get_tile_from_click(event)

        if index is None:
            return

        self.clear_hint()

        if self.selected_tile is None:
            self.select_tile(index)

        elif self.selected_tile == index:
            self.deselect_tile()

        else:
            self.puzzle.swap_tiles(self.selected_tile, index)
            self.deselect_tile()
            self.after_player_move()
            self.display_images()
            self.update_status()

    def on_right_click(self, event):  # Rotates the clicked tile

        index = self.get_tile_from_click(event)

        if index is None:
            return

        self.clear_hint()
        self.puzzle.rotate_tile(index)
        self.deselect_tile()
        self.after_player_move()
        self.display_images()
        self.update_status()

    def on_shift_left_click(self, event):  # Flips the clicked tile horizontally

        index = self.get_tile_from_click(event)

        if index is None:
            return

        self.clear_hint()
        self.puzzle.flip_tile(index, direction='horizontal')
        self.deselect_tile()
        self.after_player_move()
        self.display_images()
        self.update_status()

    def select_tile(self, index):  # Saves the selected tile and updates the dropdown

        self.selected_tile = index
        self.selected_tile_var.set(str(index))
        self.display_images()
        self.update_status()

    def deselect_tile(self):  # Clears the selected tile and updates the dropdown

        self.selected_tile = None
        self.selected_tile_var.set('')
        self.display_images()
        self.update_status()

    def rotate_selected_tile(self): #Checks that a loaded and unsolved puzzle exists before rotating

        
        if not self.__can_use_tile_controls():
            return

        try:
            
            index = int(self.selected_tile_var.get())
        except ValueError:
            messagebox.showinfo('No Tile Selected', 'Please select a tile first')
            return

        
        self.clear_hint()
        self.puzzle.rotate_tile(index)
        self.deselect_tile()
        self.after_player_move()
        self.display_images()
        self.update_status()

    def flip_selected_tile(self): #Checks that a loaded and unsolved puzzle exists before flipping

        
        if not self.__can_use_tile_controls():
            return

        try:
            
            index = int(self.selected_tile_var.get())
        except ValueError:
            messagebox.showinfo('No Tile Selected', 'Please select a tile first')
            return

        self.clear_hint()
        self.puzzle.flip_tile(index, direction='horizontal')
        self.deselect_tile()
        self.after_player_move()
        self.display_images()
        self.update_status()


    def __can_use_tile_controls(self):  # Checks that an unsolved puzzle has been loaded

        if self.puzzle.original_image is None:
            messagebox.showinfo('No Image', 'Load an image first')
            return False

        if self.puzzle.solved:
            messagebox.showinfo('Puzzle Solved', 'The puzzle is already solved')
            return False

        return True

    def after_player_move(self):  # Checks whether the latest move solved the puzzle

        if self.puzzle.check_solved():
            messagebox.showinfo('Puzzle Solved', f'Congratulations! You restored the image in {self.puzzle.moves} moves')
            self.hint_button.config(state=tk.DISABLED)

    def display_images(self):  # Displays the reference and current puzzle images

        if self.puzzle.original_image is None:
            return

        original_rgb = cv2.cvtColor(self.puzzle.original_image, cv2.COLOR_BGR2RGB)
        self.original_photo = ImageTk.PhotoImage(Image.fromarray(original_rgb))

        puzzle_rgb = cv2.cvtColor(self.puzzle.assemble_image(), cv2.COLOR_BGR2RGB)
        self.puzzle_photo = ImageTk.PhotoImage(Image.fromarray(puzzle_rgb))

        self.original_canvas.delete('all')
        self.puzzle_canvas.delete('all')

        self.original_canvas.create_image(0, 0, anchor=tk.NW, image=self.original_photo)
        self.puzzle_canvas.create_image(0, 0, anchor=tk.NW, image=self.puzzle_photo)

        self.draw_grid(self.original_canvas)
        self.draw_grid(self.puzzle_canvas)
        self.draw_tile_markers()

    def draw_grid(self, canvas):  # Draws grid lines over an image
        if self.puzzle.original_image is None:
            return

        height, width = self.puzzle.original_image.shape[:2]
        tile_width, tile_height = self.puzzle.get_tile_size()

        for index in range(1, self.puzzle.grid_size):
            x = index * tile_width
            y = index * tile_height

            canvas.create_line(x, 0, x, height, fill='#ffffff', stipple='gray50')
            canvas.create_line(0, y, width, y, fill='#ffffff', stipple='gray50')

    def draw_tile_markers(self):  # Draws selection, correctness and hint markers

        if self.puzzle.original_image is None:
            return

        tile_width, tile_height = self.puzzle.get_tile_size()

        if self.selected_tile is not None:
            x1, y1 = self.__tile_top_left(self.selected_tile)
            self.puzzle_canvas.create_rectangle(x1 + 2, y1 + 2, x1 + tile_width - 2, y1 + tile_height - 2, outline='#ffffff', width=4)

        for index in range(len(self.puzzle.tiles)):
            if self.puzzle.tile_correct(index):
                x1, y1 = self.__tile_top_left(index)
                self.puzzle_canvas.create_text(x1 + tile_width - 18, y1 + 18, text='✔', fill='#1ca12d', font=('Arial', 16, 'bold'))

        if self.hint_tile is not None:
            self.__draw_hint_circle(self.puzzle_canvas, self.hint_tile)

        if self.hint_home is not None:
            self.__draw_hint_circle(self.original_canvas, self.hint_home)

    def __tile_top_left(self, index):  # Calculates the top-left canvas position of a tile

        tile_width, tile_height = self.puzzle.get_tile_size()
        col = index % self.puzzle.grid_size
        row = index // self.puzzle.grid_size
        return col * tile_width, row * tile_height

    def __draw_hint_circle(self, canvas, index):  # Draws a circle over a hinted tile

        tile_width, tile_height = self.puzzle.get_tile_size()
        x1, y1 = self.__tile_top_left(index)
        centre_x = x1 + tile_width // 2
        centre_y = y1 + tile_height // 2
        radius = min(tile_width, tile_height) // 4

        canvas.create_oval(centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius, outline='#a0a0a0', width=5)

    def clear_hint(self):  # Clears the hint markers and redraws the images

        self.hint_tile = None
        self.hint_home = None
        self.display_images()

    def use_hint(self):  # Shows a hint if hints remain

        if self.puzzle.original_image is None or self.puzzle.solved:
            return

        if not self.puzzle.use_hint():
            if self.puzzle.hints_used >= ImagePuzzle.MAX_HINTS:
                self.hint_button.config(state=tk.DISABLED)
            return

        self.hint_tile, self.hint_home = self.puzzle.hint()

        if self.puzzle.hints_used >= ImagePuzzle.MAX_HINTS:
            self.hint_button.config(state=tk.DISABLED)

        self.display_images()
        self.update_status()

    def solve_puzzle(self):  # Solves the puzzle and updates the interface

        if self.puzzle.original_image is None:
            messagebox.showinfo('Solve', 'Load an image first')
            return

        self.puzzle.solve()
        self.deselect_tile()
        self.clear_hint()
        self.hint_button.config(state=tk.DISABLED)
        self.display_images()
        self.update_status()

    def update_status(self):  # Updates the status bar with the current puzzle information

        if self.puzzle.original_image is None:
            return

        incorrect = self.puzzle.tile_incorrect()
        hints_left = max(0, ImagePuzzle.MAX_HINTS - self.puzzle.hints_used)

        if self.puzzle.solved:
            message = f'Solved! Moves: {self.puzzle.moves} | Incorrect tiles: 0 | Hints remaining: {hints_left}'
        else:
            selected = 'None' if self.selected_tile is None else str(self.selected_tile)
            message = f'Moves: {self.puzzle.moves} | Incorrect tiles: {incorrect} | Hints remaining: {hints_left} | Selected tile: {selected}'

        self.status_var.set(message)

# Starts the Tkinter application
def main():
    root = tk.Tk()
    PuzzleCreate(root)
    root.mainloop()

# Run the program only when this file is executed
if __name__ == '__main__':
    main()


