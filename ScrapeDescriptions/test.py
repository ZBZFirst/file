import pygame
import os
import subprocess
import sys
from pygame.locals import *

# Initialize Pygame
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((1200, 800), pygame.RESIZABLE)
pygame.display.set_caption("📁 Data Historian Explorer")

# Colors
BG_COLOR = (25, 25, 40)
FOLDER_COLOR = (70, 130, 180)
SELECTED_COLOR = (100, 200, 100)
EXCLUDED_COLOR = (200, 100, 100)
TEXT_COLOR = (255, 255, 255)

# Fonts
font = pygame.font.SysFont('Arial', 24)
small_font = pygame.font.SysFont('Arial', 18)

def scan_folders(root_dir="."):
    """Scan for all folders containing data files"""
    valid_folders = []
    for root, dirs, files in os.walk(root_dir):
        if any(f.endswith(('.xlsx', '.csv')) for f in files):
            rel_path = os.path.relpath(root, root_dir)
            valid_folders.append(rel_path)
    return valid_folders

def draw_folder_selector(folders, excluded_folders, selected_index):
    """Render folder selection interface"""
    screen.fill(BG_COLOR)
    
    # Title
    title = font.render("Select Folders to Process (Click to Exclude)", True, TEXT_COLOR)
    screen.blit(title, (50, 30))
    
    # Instructions
    instructions = small_font.render("SPACE: Confirm Selection | ESC: Exit", True, TEXT_COLOR)
    screen.blit(instructions, (50, 750))
    
    # Draw folders
    for i, folder in enumerate(folders):
        color = EXCLUDED_COLOR if folder in excluded_folders else (SELECTED_COLOR if i == selected_index else FOLDER_COLOR)
        y_pos = 100 + i * 40
        
        # Folder rectangle
        pygame.draw.rect(screen, color, (50, y_pos, 1100, 35))
        
        # Folder name
        name_text = small_font.render(folder, True, TEXT_COLOR)
        screen.blit(name_text, (60, y_pos + 5))
        
        # Status indicator
        status = "EXCLUDED" if folder in excluded_folders else ""
        status_text = small_font.render(status, True, (255, 255, 255))
        screen.blit(status_text, (900, y_pos + 5))

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    folders = scan_folders(root_dir)
    excluded_folders = set()
    selected_index = 0
    confirmed = False
    
    clock = pygame.time.Clock()
    
    while not confirmed:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == K_SPACE:
                    confirmed = True
                elif event.key == K_DOWN:
                    selected_index = min(selected_index + 1, len(folders) - 1)
                elif event.key == K_UP:
                    selected_index = max(selected_index - 1, 0)
                    
            elif event.type == MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for i, _ in enumerate(folders):
                    if 50 <= mouse_pos[0] <= 1150 and 100 + i*40 <= mouse_pos[1] <= 135 + i*40:
                        selected_index = i
                        folder = folders[selected_index]
                        if folder in excluded_folders:
                            excluded_folders.remove(folder)
                        else:
                            excluded_folders.add(folder)
        
        draw_folder_selector(folders, excluded_folders, selected_index)
        pygame.display.flip()
        clock.tick(30)
    
    # Process selected folders
    selected_folders = [f for f in folders if f not in excluded_folders]
    print(f"Selected folders: {selected_folders}")
    
    # Here you would continue with your visualization pipeline
    # For now just show confirmation
    screen.fill(BG_COLOR)
    confirm_text = font.render(f"Processing {len(selected_folders)} folders...", True, TEXT_COLOR)
    screen.blit(confirm_text, (100, 100))
    pygame.display.flip()
    pygame.time.wait(2000)
    
    pygame.quit()
    return selected_folders

if __name__ == "__main__":
    selected = main()
    print("Ready to process:", selected)
