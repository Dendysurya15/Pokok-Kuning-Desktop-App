import sqlite3
import os

def get_model_names():
    """Get all model names from the model directory"""
    model_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")
    if os.path.exists(model_folder):
        model_files = [f for f in os.listdir(model_folder) if f.endswith('.pt')]
        model_names = [os.path.splitext(f)[0] for f in model_files]
        return model_names
    return []

def setup_database():
    """Create the database if it doesn't exist and set default values"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")
    conn = sqlite3.connect(db_path)
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

    # Check if we already have configuration data
    cursor.execute("SELECT COUNT(*) FROM configuration")
    count = cursor.fetchone()[0]
    
    if count == 0:
        model_names = get_model_names()
        default_model = model_names[0] if model_names else "yolov8n-pokok-kuning"

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
            "false",       # show_conf
            "Full Blok"    # status_blok
        ))
    
    conn.commit()
    conn.close()
    print("Database setup complete.")

def load_config():
    """Load configuration from database"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM configuration ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}
    
    config = {
        "model": row[1],
        "imgsz": row[2],
        "iou": row[3],
        "conf": row[4],
        "convert_shp": row[5],
        "convert_kml": row[6],
        "max_det": row[7],
        "line_width": row[8],
        "show_labels": row[9],
        "show_conf": row[10],
        "status_blok": row[11]
    }
    return config

def save_config(config):
    """Save configuration to database"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO configuration (
            model, imgsz, iou, conf, convert_shp, convert_kml,
            max_det, line_width, show_labels, show_conf, status_blok
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        config["model"], 
        config["imgsz"], 
        config["iou"], 
        config["conf"],
        config["convert_shp"], 
        config["convert_kml"],
        config["max_det"], 
        config["line_width"],
        config["show_labels"], 
        config["show_conf"],
        config["status_blok"]
    ))
    
    conn.commit()
    conn.close()
    return True
