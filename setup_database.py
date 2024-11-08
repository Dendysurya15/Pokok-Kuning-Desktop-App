import sqlite3
import requests
import json
import os

def get_model_names():
    model_folder = os.path.join(os.getcwd(), "model")
    if os.path.exists(model_folder):
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.pt')]
        model_names = [os.path.splitext(f)[0] for f in model_files]
        return model_names
    return []

def create_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            imgsz TEXT,
            iou TEXT,
            conf TEXT,
            convert_shp TEXT,
            convert_kml TEXT,
            max_det TEXT,
            line_width TEXT,
            show_labels TEXT,
            show_conf TEXT,
            status_blok TEXT
        )
    ''')

    model_names = get_model_names()
    default_model = model_names[0] if model_names else ""

    # Insert default values
    cursor.execute('''
        INSERT INTO configuration (
            model, imgsz, iou, conf, convert_shp, convert_kml, 
            max_det, line_width, show_labels, show_conf, status_blok
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        default_model,  # model
        "1280",        # imgsz
        "0.2",         # iou
        "0.2",         # conf
        "true",        # convert_shp
        "false",       # convert_kml
        "12000",       # max_det
        "3",           # line_width
        "false",       # show_labels
        "false",        # show_conf
        "true"        # status_blok
    ))
    
    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    create_database()
